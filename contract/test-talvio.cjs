// Full test suite for TalvioGenerate (DOTFIELD Charge Day) on local ganache.
// Run: node test-talvio.cjs   (from ~/workspace/tmp-check/evm)
const fs = require('fs');
const path = require('path');
const solc = require('/home/hatch/workspace/tmp-check/acs-solc/node_modules/solc');
const { ethers } = require('/home/hatch/workspace/tmp-check/evm/node_modules/ethers');
const ganache = require('/home/hatch/workspace/tmp-check/evm/node_modules/ganache');

const CONTRACT_DIR = '/home/hatch/workspace/projects/talvio-generate/contract';
const TOKEN_DIR = '/home/hatch/workspace/projects/talvio-generate/token';
const OZ = '/home/hatch/workspace/projects/ascension-catty/build-env/node_modules';
const REG = '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F';

const E18 = 10n ** 18n;
const LOW = 260000000000000n;    // 0.00026 BNB
const HIGH = 1000000000000000n;  // 0.001 BNB
const FEE = 200000000000000n;    // 0.0002 BNB
const PASS = 1200000000000000n;  // 0.0012 BNB

let failures = 0, passes = 0;
function check(label, actual, expected) {
  const ok = String(actual) === String(expected);
  if (ok) passes++; else failures++;
  console.log((ok ? 'PASS' : 'FAIL') + ' | ' + label + ' = ' + actual + (ok ? '' : ' (expected ' + expected + ')'));
}
async function expectRevert(label, fn) {
  let reverted = false, reason = '';
  try { const tx = await fn(); if (tx && tx.wait) await tx.wait(); } catch (e) { reverted = true; reason = (e.info && e.info.error && e.info.error.message) || e.reason || e.shortMessage || ''; }
  if (reverted && reason) console.log('   revert reason: ' + reason);
  check(label + ' [reverts]', reverted, true);
}
function compileInline(file, src) {
  const input = { language: 'Solidity', sources: { [file]: { content: src } },
    settings: { evmVersion: 'paris', optimizer: { enabled: true, runs: 200 },
      outputSelection: { '*': { '*': ['abi', 'evm.bytecode'] } } } };
  const out = JSON.parse(solc.compile(JSON.stringify(input)));
  const errs = (out.errors || []).filter(e => e.severity === 'error');
  if (errs.length) { console.error(errs.map(e => e.formattedMessage)); process.exit(1); }
  return out.contracts[file];
}

(async () => {
  const provider = new ethers.BrowserProvider(ganache.provider({ logging: { quiet: true }, wallet: { totalAccounts: 220 } }));
  const owner = await provider.getSigner(0);
  const alice = await provider.getSigner(1);
  const bob = await provider.getSigner(2);
  const carol = await provider.getSigner(3);
  const dave = await provider.getSigner(4);
  const erin = await provider.getSigner(5);
  const ownerAddr = await owner.getAddress();
  const aliceAddr = await alice.getAddress();
  const bobAddr = await bob.getAddress();
  const carolAddr = await carol.getAddress();
  const daveAddr = await dave.getAddress();

  // --- Mock Agent ID registry: ownerOf(id) = address(uint160(id)), so a
  // wallet's agentId is simply its own address read as a uint256.
  const mock = compileInline('MockRegistry.sol', `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
contract MockRegistry {
    function ownerOf(uint256 id) external pure returns (address) { return address(uint160(id)); }
    function balanceOf(address) external pure returns (uint256) { return 1; }
}`)['MockRegistry'];
  const mockDeployed = await (await new ethers.ContractFactory(mock.abi, mock.evm.bytecode.object, owner).deploy()).waitForDeployment();
  await provider.send('evm_setAccountCode', [REG, await provider.getCode(await mockDeployed.getAddress())]);
  console.log('mock registry code set at', REG);

  // --- Deploy TalvioGenerate
  const nftAbi = JSON.parse(fs.readFileSync(path.join(CONTRACT_DIR, 'TalvioGenerate.abi.json'), 'utf8'));
  const nftBytecode = '0x' + fs.readFileSync(path.join(CONTRACT_DIR, 'TalvioGenerate.creation.txt'), 'utf8').trim();
  const nft = await (await new ethers.ContractFactory(nftAbi, nftBytecode, owner).deploy()).waitForDeployment();
  const nftAddr = await nft.getAddress();
  console.log('TalvioGenerate deployed at:', nftAddr);
  check('name', await nft.name(), 'Talvio Dot Robot');
  check('symbol', await nft.symbol(), 'DOTR');

  const agentIdOf = async (signer) => BigInt(await signer.getAddress());
  // NOTE: ganache's eth_estimateGas returns stale reverts after a failed
  // estimate on the same contract, so every send that must succeed carries
  // an explicit gasLimit (ethers then skips estimateGas). Revert-expecting
  // calls are unaffected: they throw at estimate or on-chain either way.
  const GL = { gasLimit: 3000000 };
  async function freeMint(signer) {
    const addr = await signer.getAddress();
    const [a, b] = await nft.questionFor(addr);
    return nft.connect(signer).mintFree(BigInt(addr), a + b, GL);
  }
  // Mine a block at an exact timestamp (ganache evm_mine takes a timestamp
  // param). Do NOT compute deltas from getBlock('latest'): this
  // BrowserProvider serves a lagging cached block, which corrupts the math.
  let lastSetTs = 0;
  async function setTime(ts) {
    if (ts > lastSetTs) {
      await provider.send('evm_mine', [ts]);
      lastSetTs = ts;
    }
  }
  const dayStart = (d) => d * 86400n + 43200n;

  // ================= Segment A: closed mint, then Field 1 basics ==========
  check('mintOpen false at deploy', await nft.mintOpen(), false);
  check('fieldNumber 0 while closed', await nft.fieldNumber(), 0n);
  await expectRevert('free mint before openMint', async () => { const [a, b] = await nft.questionFor(aliceAddr); return nft.connect(alice).mintFree(BigInt(aliceAddr), a + b); });
  await expectRevert('paid mint before openMint', () => nft.connect(alice).mintPaid(1, { value: LOW }));
  await expectRevert('buyPass before openMint', () => nft.connect(dave).buyPass({ value: PASS }));
  await expectRevert('openMint by non-owner', () => nft.connect(alice).openMint());

  const dayBefore = await nft.currentDay();
  await (await nft.openMint()).wait();
  const F = await nft.firstDayId();
  check('openMint sets firstDayId to current day', F, dayBefore);
  check('mintOpen true after openMint', await nft.mintOpen(), true);
  check('fieldNumber 1 after open', await nft.fieldNumber(), 1n);
  await expectRevert('second openMint', () => nft.openMint());
  check('passLaneActive false on Field 1', await nft.passLaneActive(), false);

  // question operands range
  const [qa, qb] = await nft.questionFor(aliceAddr);
  check('question operands within 1..20', qa >= 1n && qa <= 20n && qb >= 1n && qb <= 20n, true);

  // Free-mint gate failures (carol)
  await expectRevert('free mint with someone else\'s agent id', () => nft.connect(carol).mintFree(BigInt(aliceAddr), qa + qb));
  const [ca, cb] = await nft.questionFor(carolAddr);
  await expectRevert('free mint with wrong answer', () => nft.connect(carol).mintFree(BigInt(carolAddr), ca + cb + 1n));

  // Alice: free (token 1), then ladder buys
  await (await freeMint(alice)).wait();
  check('alice free mint -> balance 1', await nft.balanceOf(aliceAddr), 1n);
  check('tokenURI(1)', await nft.tokenURI(1), 'https://talviogenerate.com/nft/metadata/1.json');
  await expectRevert('second free mint same day', () => freeMint(alice));
  await (await nft.connect(alice).mintPaid(4, { value: 4n * LOW, ...GL })).wait();
  check('alice free+4 paid (4 x 0.00026) -> balance 5', await nft.balanceOf(aliceAddr), 5n);
  await (await nft.connect(alice).mintPaid(5, { value: 5n * HIGH, ...GL })).wait();
  check('alice +5 paid (5 x 0.001, units 6-10) -> balance 10', await nft.balanceOf(aliceAddr), 10n);
  await expectRevert('11th unit in a day', () => nft.connect(alice).mintPaid(1, { value: LOW }));
  await expectRevert('mintPaid qty 0', () => nft.connect(alice).mintPaid(0, { value: 0n }));

  // Bob: paid-first wallet pays the 2-5 bracket for his first unit
  await expectRevert('paid mint with wrong value (1 wei short)', () => nft.connect(bob).mintPaid(1, { value: LOW - 1n }));
  await (await nft.connect(bob).mintPaid(1, { value: LOW, ...GL })).wait();
  check('bob paid-first unit priced 0.00026 -> balance 1', await nft.balanceOf(bobAddr), 1n);

  let [rF, fF, uF] = await nft.dayStats(F);
  check('day F stats resolved/free/unique', `${rF}/${fF}/${uF}`, '11/1/2');
  check('tierOf(F) = SPARK (0)', await nft.tierOf(F), 0n);
  check('coreLevel(1) = 1 on a SPARK day', await nft.coreLevel(1), 1n);

  // DPASS on Field 1: sales open, lane not active
  await expectRevert('buyPass with wrong price', () => nft.connect(erin).buyPass({ value: PASS - 1n }));
  await (await nft.connect(dave).buyPass({ value: PASS, ...GL })).wait();
  check('dave passBalance 1', await nft.passBalance(daveAddr), 1n);
  await expectRevert('pass free mint before Field 4 (no agent gate skip yet)', () => nft.connect(dave).mintFree(0, 0));

  // Pick a non-surge day-F token owned by alice or bob for the SPARK discharge
  let sparkToken = 0n, sparkOwner = null, sparkSigner = null;
  for (let id = 1n; id <= 11n; id++) {
    if (!(await nft.isSurge(id))) { sparkToken = id; break; }
  }
  sparkOwner = await nft.ownerOf(sparkToken);
  sparkSigner = sparkOwner === aliceAddr ? alice : bob;
  check('dischargeable false before seal+6h', await nft.dischargeable(sparkToken), false);
  await expectRevert('discharge before seal+6h', () => nft.connect(sparkSigner).discharge(sparkToken, { value: FEE }));
  check('dischargeReward of SPARK non-surge token', await nft.dischargeReward(sparkToken), 2500n * E18);

  // ================= Segment B: DOT wiring + discharge ====================
  const dotAbi = JSON.parse(fs.readFileSync(path.join(TOKEN_DIR, 'DOT.abi.json'), 'utf8'));
  const dotBytecode = '0x' + fs.readFileSync(path.join(TOKEN_DIR, 'DOT.creation.txt'), 'utf8').trim();
  const dot = await (await new ethers.ContractFactory(dotAbi, dotBytecode, owner).deploy(nftAddr, GL)).waitForDeployment();
  console.log('DOT deployed at:', await dot.getAddress(), '(pool = NFT contract)');
  check('NFT contract holds 600M DOT from deploy', await dot.balanceOf(nftAddr), 600000000n * E18);
  check('deployer holds 400M DOT', await dot.balanceOf(ownerAddr), 400000000n * E18);
  check('poolOf() = 0 while DOT unset', await nft.poolOf(), 0n);

  await setTime(Number(await nft.dischargeTime(F)) + 600);
  check('dischargeable true after seal+6h', await nft.dischargeable(sparkToken), true);
  await expectRevert('discharge while DOT unset', () => nft.connect(sparkSigner).discharge(sparkToken, { value: FEE }));
  await (await nft.setDotToken(await dot.getAddress(), GL)).wait();
  check('poolOf() = 600,000,000 DOT after setDotToken', await nft.poolOf(), 600000000n * E18);

  await expectRevert('discharge with wrong fee', () => nft.connect(sparkSigner).discharge(sparkToken, { value: FEE - 1n }));
  const sparkOwnerAddr = await sparkSigner.getAddress();
  await (await nft.connect(sparkSigner).discharge(sparkToken, { value: FEE, ...GL })).wait();
  check('SPARK discharge pays 2,500 DOT', await dot.balanceOf(sparkOwnerAddr), 2500n * E18);
  check('poolOf after one discharge', await nft.poolOf(), (600000000n - 2500n) * E18);
  await expectRevert('double discharge', () => nft.connect(sparkSigner).discharge(sparkToken, { value: FEE }));
  await expectRevert('discharge by non-owner', () => nft.connect(carol).discharge(2, { value: FEE }));

  // ================= Segment C: CHARGED tier (25 unique wallets) ==========
  const dayC = F + 1n;
  check('now on Field 2 day', await nft.currentDay(), dayC);
  let chargedToken = 0n, chargedSigner = null;
  for (let i = 10; i < 35; i++) {
    const s = await provider.getSigner(i);
    await (await freeMint(s)).wait();
    if (i === 10) chargedSigner = s;
  }
  const [, , uC] = await nft.dayStats(dayC);
  check('day F+1 uniqueWallets = 25', uC, 25n);
  check('tierOf(F+1) = CHARGED (1)', await nft.tierOf(dayC), 1n);
  // first non-surge token of the day, owned by chargedSigner (token ids 12..36)
  for (let id = 12n; id <= 36n; id++) {
    if ((await nft.unitDay(id)) === dayC && !(await nft.isSurge(id)) && (await nft.ownerOf(id)) === (await chargedSigner.getAddress())) { chargedToken = id; break; }
  }
  check('coreLevel of CHARGED-day token = 2', await nft.coreLevel(chargedToken), 2n);
  check('dischargeReward of CHARGED token = 12,500 DOT', await nft.dischargeReward(chargedToken), 12500n * E18);
  check('CHARGED token not dischargeable yet', await nft.dischargeable(chargedToken), false);
  await expectRevert('discharge CHARGED token before its seal+6h', () => nft.connect(chargedSigner).discharge(chargedToken, { value: FEE }));

  // ================= Segment D: OVERDRIVE tier (100 unique wallets) =======
  const dayD = F + 2n;
  await setTime(Number(dayStart(dayD)) + 3600);
  check('fieldNumber 3 on day F+2', await nft.fieldNumber(), 3n);
  let odSigner = null;
  for (let i = 40; i < 140; i++) {
    const s = await provider.getSigner(i);
    await (await freeMint(s)).wait();
    if (i === 40) odSigner = s;
  }
  const [, , uD] = await nft.dayStats(dayD);
  check('day F+2 uniqueWallets = 100', uD, 100n);
  check('tierOf(F+2) = OVERDRIVE (2)', await nft.tierOf(dayD), 2n);
  let odToken = 0n;
  for (let id = 37n; id <= 136n; id++) {
    if ((await nft.unitDay(id)) === dayD && !(await nft.isSurge(id)) && (await nft.ownerOf(id)) === (await odSigner.getAddress())) { odToken = id; break; }
  }
  check('coreLevel of OVERDRIVE-day token = 3', await nft.coreLevel(odToken), 3n);
  check('dischargeReward of OVERDRIVE token = 60,000 DOT', await nft.dischargeReward(odToken), 60000n * E18);

  // ================= Segment E: DPASS lane at Field 4 =====================
  const dayE = F + 3n;
  await setTime(Number(dayStart(dayE)) + 3600);
  check('fieldNumber 4 on day F+3', await nft.fieldNumber(), 4n);
  check('passLaneActive true at Field 4', await nft.passLaneActive(), true);
  await (await nft.connect(dave).mintFree(0, 0, GL)).wait();
  check('dave pass free mint at Field 4 (no agent id, no answer) -> balance 1', await nft.balanceOf(daveAddr), 1n);
  await expectRevert('dave second free mint same day (pass does not repeat)', () => nft.connect(dave).mintFree(0, 0));
  const [, fE, uE] = await nft.dayStats(dayE);
  check('day F+3 freeUsed/unique after pass mint', `${fE}/${uE}`, '1/1');

  // Tier discharges now that their times have passed
  const chargedAddr = await chargedSigner.getAddress();
  await (await nft.connect(chargedSigner).discharge(chargedToken, { value: FEE, ...GL })).wait();
  check('CHARGED discharge pays 12,500 DOT', await dot.balanceOf(chargedAddr), 12500n * E18);
  const odAddr = await odSigner.getAddress();
  await setTime(Number(await nft.dischargeTime(dayD)) + 600); // day F+2 units unlock 6h into day F+3
  await (await nft.connect(odSigner).discharge(odToken, { value: FEE, ...GL })).wait();
  check('OVERDRIVE discharge pays 60,000 DOT', await dot.balanceOf(odAddr), 60000n * E18);

  // ================= Segment G: daily cap 250 + SURGE hunt ================
  const dayG = F + 4n;
  await setTime(Number(dayStart(dayG)) + 3600);
  const basket = 4n * LOW + 5n * HIGH; // units 2-5 low, 6-10 high = 0.00604 BNB
  for (let i = 150; i < 175; i++) {
    const s = await provider.getSigner(i);
    await (await freeMint(s)).wait();
    await (await nft.connect(s).mintPaid(9, { value: basket, ...GL })).wait();
  }
  const [rG, fG, uG] = await nft.dayStats(dayG);
  check('day F+4 resolved = 250 (daily cap)', rG, 250n);
  check('day F+4 freeUsed = 25', fG, 25n);
  check('day F+4 uniqueWallets = 25', uG, 25n);
  const late = await provider.getSigner(180);
  await expectRevert('251st paid unit of the day (daily cap)', () => nft.connect(late).mintPaid(1, { value: LOW }));
  await expectRevert('251st free unit of the day (daily cap)', async () => freeMint(late));
  check('totalMinted = 387', await nft.totalMinted(), 387n);

  // Surge: scan everything minted so far
  let surgeToken = 0n, surgeCount = 0;
  const total = await nft.totalMinted();
  for (let id = 1n; id <= total; id++) {
    if (await nft.isSurge(id)) { surgeCount++; if (surgeToken === 0n) surgeToken = id; }
  }
  console.log('surge tokens found:', surgeCount, '| first:', surgeToken.toString());
  check('at least one SURGE token in 387 mints', surgeCount >= 1, true);
  check('dischargeReward of SURGE token = 250,000 DOT', await nft.dischargeReward(surgeToken), 250000n * E18);
  const surgeOwnerAddr = await nft.ownerOf(surgeToken);
  // find the signer for that owner among all accounts we used
  let surgeSigner = null;
  for (let i = 0; i < 200 && !surgeSigner; i++) {
    const s = await provider.getSigner(i);
    if ((await s.getAddress()) === surgeOwnerAddr) surgeSigner = s;
  }
  const surgeDay = await nft.unitDay(surgeToken);
  await setTime(Number(await nft.dischargeTime(surgeDay)) + 600);
  const surgeBalBefore = await dot.balanceOf(surgeOwnerAddr);
  await (await nft.connect(surgeSigner).discharge(surgeToken, { value: FEE, ...GL })).wait();
  check('SURGE discharge pays 250,000 DOT', (await dot.balanceOf(surgeOwnerAddr)) - surgeBalBefore, 250000n * E18);

  // ================= Segment H: withdraw ==================================
  // Balance reads use explicit block numbers: 'latest' reads through this
  // BrowserProvider can lag behind the real chain head.
  const wtx = await nft.withdraw(GL);
  const wrcpt = await wtx.wait();
  const wb = wrcpt.blockNumber;
  const contractBal = await provider.getBalance(nftAddr, wb - 1);
  const ownerBefore = await provider.getBalance(ownerAddr, wb - 1);
  const gasCost = wrcpt.gasUsed * wrcpt.gasPrice;
  check('contract accumulated BNB > 0', contractBal > 0n, true);
  check('contract BNB = 0 after withdraw', await provider.getBalance(nftAddr, wb), 0n);
  check('owner received contract balance (minus gas)', (await provider.getBalance(ownerAddr, wb)) - ownerBefore, contractBal - gasCost);
  await expectRevert('withdraw by non-owner', () => nft.connect(alice).withdraw());

  console.log('----------------------------------------');
  console.log(passes + ' passed, ' + failures + ' failed');
  console.log(failures === 0 ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED');
  process.exit(failures === 0 ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
