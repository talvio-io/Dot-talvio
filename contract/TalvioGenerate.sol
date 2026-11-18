// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @notice Minimal view of the Binance Agent ID registry (SPACE ID).
interface IAgentRegistry {
    function ownerOf(uint256 agentId) external view returns (address);
}

/// @title TalvioGenerate — DOTFIELD Charge Day NFT (BNB Chain)
/// @notice Daily Field mechanics:
///         - One Field per day, sealing at 12:00 UTC. A day's units are
///           resolved (minted) only during that day; the day's charge tier is
///           set by how many unique wallets resolved that day and is stamped
///           permanently on every unit of the day (its Core Level).
///         - Free: 1 unit per wallet per day, first unit of the day only,
///           gated by a Binance Agent ID + an on-chain anti-bot question.
///         - Paid ladder (same day, per unit index): units 2-5 cost
///           0.00026 BNB, units 6-10 cost 0.001 BNB; max 10 units/day/wallet.
///         - Discharge (the second act): from seal + 6h, each sealed unit
///           discharges exactly once, claiming $DOT from this contract's pool
///           for a 0.0002 BNB fee. Claims never expire.
///         - SURGE units (~3%, gold core) claim 250,000 DOT.
///         - DPASS: a non-transferable pass balance. Holders resolve free
///           with no Agent ID and no question once the pass lane is active
///           (Field No 4). Pass sales open together with Field No 1.
/// @dev    MINT STARTS CLOSED. Nothing can be resolved until the owner calls
///         openMint(). Field No of a day = dayId - firstDayId + 1.
contract TalvioGenerate is ERC721, Ownable {
    using Strings for uint256;

    // --- Constants -----------------------------------------------------------
    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public constant DAILY_CAP = 250;
    uint256 public constant FREE_QUOTA = 150;
    uint256 public constant MAX_PER_WALLET_PER_DAY = 10;
    uint256 public constant PRICE_LOW = 260000000000000; // 0.00026 BNB, units 2-5
    uint256 public constant PRICE_HIGH = 1000000000000000; // 0.001 BNB, units 6-10
    uint256 public constant DISCHARGE_FEE = 200000000000000; // 0.0002 BNB
    uint256 public constant PASS_PRICE = 1200000000000000; // 0.0012 BNB
    address public constant AGENT_REGISTRY = 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F;

    uint256 public constant REWARD_SPARK = 2500 * 10 ** 18;
    uint256 public constant REWARD_CHARGED = 12500 * 10 ** 18;
    uint256 public constant REWARD_OVERDRIVE = 60000 * 10 ** 18;
    uint256 public constant REWARD_SURGE = 250000 * 10 ** 18;

    // --- State ---------------------------------------------------------------
    bool public mintOpen;
    uint256 public firstDayId; // currentDay() at the moment openMint() ran
    uint256 public totalMinted;
    string public baseURI;
    IERC20 public dotToken;

    struct DayStats {
        uint256 resolved;
        uint256 freeUsed;
        uint256 uniqueWallets;
    }

    mapping(uint256 => DayStats) private _days;
    mapping(uint256 => mapping(address => uint256)) public walletDayCount;
    mapping(uint256 => mapping(address => bool)) private _seenThatDay;
    mapping(uint256 => uint256) public unitDay;
    mapping(uint256 => bool) public surgeOf;
    mapping(uint256 => bool) public dischargedOf;
    mapping(address => uint256) public passBalance;

    // --- Events --------------------------------------------------------------
    event MintOpened(uint256 firstDayId);
    event Resolved(address indexed wallet, uint256 indexed tokenId, uint256 indexed dayId, bool paid);
    event Discharged(uint256 indexed tokenId, address indexed wallet, uint256 reward);
    event PassPurchased(address indexed wallet, uint256 passBalance);
    event DotTokenSet(address dotToken);
    event BaseURISet(string baseURI);
    event Withdrawn(address indexed owner, uint256 amount);

    constructor() ERC721("Talvio Dot Robot", "DOTR") Ownable(msg.sender) {
        baseURI = "https://talviogenerate.com/nft/metadata/";
        // mintOpen stays false: the owner opens Field No 1 explicitly.
    }

    // --- Day / Field math ------------------------------------------------------
    /// @notice Day index; a Charge Day runs 12:00 UTC -> 12:00 UTC.
    function currentDay() public view returns (uint256) {
        return (block.timestamp - 43200) / 86400;
    }

    /// @notice Field number of the current day (0 while mint is closed).
    function fieldNumber() public view returns (uint256) {
        if (!mintOpen) return 0;
        return currentDay() - firstDayId + 1;
    }

    /// @notice When a day's units become dischargeable: next day's seal
    ///         (12:00 UTC) + 6 hours.
    function dischargeTime(uint256 dayId) public pure returns (uint256) {
        return (dayId + 1) * 86400 + 43200 + 21600;
    }

    // --- Owner -----------------------------------------------------------------
    /// @notice Opens the mint and starts Field No 1 on the current day.
    function openMint() external onlyOwner {
        require(!mintOpen, "already open");
        mintOpen = true;
        firstDayId = currentDay();
        emit MintOpened(firstDayId);
    }

    function setDotToken(address token) external onlyOwner {
        require(token != address(0), "zero address");
        dotToken = IERC20(token);
        emit DotTokenSet(token);
    }

    function setBaseURI(string calldata uri) external onlyOwner {
        baseURI = uri;
        emit BaseURISet(uri);
    }

    function withdraw() external onlyOwner {
        uint256 amount = address(this).balance;
        require(amount > 0, "nothing to withdraw");
        (bool ok, ) = owner().call{value: amount}("");
        require(ok, "withdraw failed");
        emit Withdrawn(owner(), amount);
    }

    // --- Anti-bot question -------------------------------------------------------
    /// @notice Deterministic per (day, wallet) addition question, operands 1..20.
    function questionFor(address wallet) public view returns (uint256 a, uint256 b) {
        uint256 h = uint256(keccak256(abi.encode(currentDay(), wallet, "DOTFIELD-QUESTION")));
        a = (h % 20) + 1;
        b = ((h >> 128) % 20) + 1;
    }

    // --- DPASS -------------------------------------------------------------------
    /// @notice The pass lane: pass holders skip the Agent ID + question gate
    ///         from Field No 4 onward.
    function passLaneActive() public view returns (bool) {
        return mintOpen && (currentDay() - firstDayId) >= 3;
    }

    /// @notice Buy one DPASS (non-transferable balance). Sales open with Field No 1.
    function buyPass() external payable {
        require(mintOpen, "mint closed");
        require(msg.value == PASS_PRICE, "exact pass price");
        passBalance[msg.sender] += 1;
        emit PassPurchased(msg.sender, passBalance[msg.sender]);
    }

    // --- Resolve (mint) ------------------------------------------------------------
    /// @notice The day's first unit, free. Gate: Binance Agent ID ownership +
    ///         the anti-bot answer — both skipped for DPASS holders once the
    ///         pass lane is active (Field No 4+).
    function mintFree(uint256 agentId, uint256 answer) external {
        require(mintOpen, "mint closed");
        uint256 day = currentDay();
        require(totalMinted < MAX_SUPPLY, "sold out");
        DayStats storage ds = _days[day];
        require(ds.resolved < DAILY_CAP, "daily cap reached");
        require(ds.freeUsed < FREE_QUOTA, "free quota exhausted");
        require(walletDayCount[day][msg.sender] == 0, "free is the first unit only");

        bool passOk = passLaneActive() && passBalance[msg.sender] > 0;
        if (!passOk) {
            require(IAgentRegistry(AGENT_REGISTRY).ownerOf(agentId) == msg.sender, "not your agent id");
            (uint256 a, uint256 b) = questionFor(msg.sender);
            require(answer == a + b, "wrong answer");
        }
        _resolve(day, false);
    }

    /// @notice Paid units on the day's ladder. Exact payment required.
    ///         Price is by unit index in the day (1-indexed): indices 2-5 cost
    ///         PRICE_LOW, indices 6-10 cost PRICE_HIGH. A paid unit at index 1
    ///         (wallet skipped its free unit) is priced as index 2.
    function mintPaid(uint256 qty) external payable {
        require(mintOpen, "mint closed");
        require(qty >= 1, "qty 0");
        uint256 day = currentDay();
        uint256 count = walletDayCount[day][msg.sender];
        require(count + qty <= MAX_PER_WALLET_PER_DAY, "daily wallet cap");
        require(_days[day].resolved + qty <= DAILY_CAP, "daily cap reached");
        require(totalMinted + qty <= MAX_SUPPLY, "sold out");

        uint256 total = 0;
        for (uint256 i = 1; i <= qty; i++) {
            uint256 idx = count + i;
            uint256 eff = idx < 2 ? 2 : idx;
            total += eff <= 5 ? PRICE_LOW : PRICE_HIGH;
        }
        require(msg.value == total, "exact payment required");

        for (uint256 i = 0; i < qty; i++) {
            _resolve(day, true);
        }
    }

    function _resolve(uint256 day, bool paid) internal {
        totalMinted += 1;
        uint256 tokenId = totalMinted;
        unitDay[tokenId] = day;

        uint256 seed = uint256(keccak256(abi.encode(tokenId, msg.sender, block.prevrandao, block.timestamp)));
        surgeOf[tokenId] = seed % 1000 >= 970;

        DayStats storage ds = _days[day];
        ds.resolved += 1;
        if (!paid) ds.freeUsed += 1;
        walletDayCount[day][msg.sender] += 1;
        if (!_seenThatDay[day][msg.sender]) {
            _seenThatDay[day][msg.sender] = true;
            ds.uniqueWallets += 1;
        }

        _safeMint(msg.sender, tokenId);
        emit Resolved(msg.sender, tokenId, day, paid);
    }

    // --- Tier / core -----------------------------------------------------------------
    /// @notice 0 = SPARK (<25 unique wallets), 1 = CHARGED (25-99), 2 = OVERDRIVE (100+).
    function tierOf(uint256 dayId) public view returns (uint8) {
        uint256 u = _days[dayId].uniqueWallets;
        if (u >= 100) return 2;
        if (u >= 25) return 1;
        return 0;
    }

    /// @notice The day's charge tier stamped on the unit: Core Level 1..3.
    function coreLevel(uint256 tokenId) public view returns (uint256) {
        require(_ownerOf(tokenId) != address(0), "no such token");
        return uint256(tierOf(unitDay[tokenId])) + 1;
    }

    function isSurge(uint256 tokenId) public view returns (bool) {
        return surgeOf[tokenId];
    }

    // --- Discharge ---------------------------------------------------------------------
    function dischargeable(uint256 tokenId) public view returns (bool) {
        if (_ownerOf(tokenId) == address(0)) return false;
        if (dischargedOf[tokenId]) return false;
        return block.timestamp >= dischargeTime(unitDay[tokenId]);
    }

    /// @notice The DOT this unit would claim right now (0 if not minted).
    function dischargeReward(uint256 tokenId) public view returns (uint256) {
        if (_ownerOf(tokenId) == address(0)) return 0;
        if (surgeOf[tokenId]) return REWARD_SURGE;
        uint8 tier = tierOf(unitDay[tokenId]);
        if (tier == 2) return REWARD_OVERDRIVE;
        if (tier == 1) return REWARD_CHARGED;
        return REWARD_SPARK;
    }

    /// @notice Claim the unit's DOT, once, for exactly 0.0002 BNB. Never expires.
    function discharge(uint256 tokenId) external payable {
        require(ownerOf(tokenId) == msg.sender, "not token owner");
        require(!dischargedOf[tokenId], "already discharged");
        require(block.timestamp >= dischargeTime(unitDay[tokenId]), "not yet dischargeable");
        require(msg.value == DISCHARGE_FEE, "exact discharge fee");
        require(address(dotToken) != address(0), "DOT not set");
        uint256 reward = dischargeReward(tokenId);
        require(dotToken.balanceOf(address(this)) >= reward, "pool insufficient");

        dischargedOf[tokenId] = true;
        require(dotToken.transfer(msg.sender, reward), "DOT transfer failed");
        emit Discharged(tokenId, msg.sender, reward);
    }

    /// @notice DOT held by this contract as the claim pool (0 while unset).
    function poolOf() public view returns (uint256) {
        if (address(dotToken) == address(0)) return 0;
        return dotToken.balanceOf(address(this));
    }

    // --- Views for the site --------------------------------------------------------------
    function dayStats(uint256 dayId) public view returns (uint256 resolved, uint256 freeUsed, uint256 uniqueWallets) {
        DayStats storage ds = _days[dayId];
        return (ds.resolved, ds.freeUsed, ds.uniqueWallets);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "no such token");
        return string.concat(baseURI, tokenId.toString(), ".json");
    }
}
