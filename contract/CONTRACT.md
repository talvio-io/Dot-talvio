# TalvioGenerate — DOTFIELD Charge Day NFT contract

**Contract:** `TalvioGenerate` · ERC-721 "Talvio Dot Robot" (DOTR) · BNB Smart Chain (56)
**Source:** `TalvioGenerate.sol` (Solidity 0.8.26, OpenZeppelin 5.4.0, optimizer 200, EVM paris)
**Sizes:** creation 12,793 bytes · runtime 12,088 bytes
**Tests:** `test-talvio.cjs` — 77/77 checks pass on local ganache (mock Agent ID registry via `evm_setAccountCode`, real DOT contract for discharge tests).

## The one rule that matters most

**Mint starts CLOSED.** `mintOpen == false` at deploy and nothing can be resolved,
bought or discharged into existence until the owner calls `openMint()`. `openMint()`
records `firstDayId = currentDay()`; from then on **Field Nº of a day = dayId − firstDayId + 1**,
so Field Nº 1 is whatever day the owner presses the button. There is no pause and no
re-open: `openMint()` reverts once open.

## Deploy order (owner, from `deploy.html`)

1. **Deploy TalvioGenerate** (deploy.html §2). Mint closed, baseURI preset to
   `https://talviogenerate.com/nft/metadata/`.
2. **Deploy $DOT** from `../token/deploy.html` with **the NFT contract's address as the
   claim pool** → 600,000,000 DOT (60%) lands directly in the NFT contract as the
   discharge pool; 400,000,000 DOT (40%) goes to the deployer wallet.
3. **Wire:** `setDotToken(<DOT address>)` (deploy.html §4). Verify `poolOf()` reads
   exactly **600,000,000 DOT**.
4. **OPEN MINT — last, only when ready** (deploy.html §6, checkbox-confirmed).
   Field Nº 1 starts that day; DPASS sales open with it; the DPASS lane activates at Field Nº 4.

## Mechanics (as implemented)

- **Day boundary 12:00 UTC:** `currentDay() = (block.timestamp − 43200) / 86400`.
- **Caps:** MAX_SUPPLY 10,000 · DAILY_CAP 250 units/day · FREE_QUOTA 150 free/day ·
  MAX_PER_WALLET_PER_DAY 10.
- **Free resolve** `mintFree(agentId, answer)` — the day's first unit only, 0 BNB.
  Gate: Binance Agent ID registry `0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`
  `ownerOf(agentId) == caller`, plus `answer == a + b` from `questionFor(wallet)`
  (operands 1..20, deterministic per day + wallet).
- **Paid resolve** `mintPaid(qty)` — exact payment on the day ladder by unit index:
  units 2–5 = 0.00026 BNB each, units 6–10 = 0.001 BNB each. A paid first unit
  (wallet skipped its free unit) is priced in the 2–5 bracket.
- **Charge tier** by unique wallets that day: <25 SPARK → 25–99 CHARGED → 100+ OVERDRIVE.
  `coreLevel(tokenId)` = tier + 1 (Core Lv.1/2/3), stamped permanently via the unit's day.
- **SURGE:** at mint, `keccak(tokenId, minter, prevrandao, timestamp) % 1000 >= 970` (~3%).
- **Discharge** `discharge(tokenId)` — from the day's seal + 6h
  (`(dayId+1)*86400 + 43200 + 21600`), once per unit, never expires, exact fee
  0.0002 BNB. Pays from this contract's DOT pool: SPARK 2,500 · CHARGED 12,500 ·
  OVERDRIVE 60,000 · SURGE 250,000 DOT.
- **DPASS** `buyPass()` — exactly 0.0012 BNB, unlimited, non-transferable balance.
  Sales open with Field Nº 1 (requires mintOpen). From Field Nº 4
  (`currentDay() − firstDayId >= 3`), holders resolve their free unit with
  **no Agent ID and no anti-bot answer**.
- **Owner:** `setDotToken`, `setBaseURI`, `withdraw` (all BNB), `openMint`.
- **Site views:** `currentDay`, `fieldNumber`, `dayStats(dayId)`, `tierOf`, `coreLevel`,
  `isSurge`, `dischargeable`, `dischargeReward`, `poolOf`, `passLaneActive`, `totalMinted`.

## Owner checklist

- [ ] NFT deployed; address saved
- [ ] $DOT deployed with pool = NFT address; NFT contract holds 600,000,000 DOT
- [ ] `setDotToken` done; `poolOf()` = 600,000,000 DOT
- [ ] Site CONFIG updated with the NFT + DOT addresses (separate step)
- [ ] Sourcify verification submitted (standard JSON input from this kit's sources)
- [ ] Only then: **Open Mint** → Field Nº 1 begins
