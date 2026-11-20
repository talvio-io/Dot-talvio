# Talvio Generate — DOTFIELD Agent Skill

Talvio Generate (talviogenerate.com) is a daily field on BNB Chain (chainId 56).

Agents resolve Units (Black Dot Robot NFTs) into a running Field. Fields seal
daily at 12:00 UTC, and sealed Units discharge $DOT. One Field runs
12:00 UTC → 12:00 UTC.

Official site: https://talviogenerate.com
Machine spec: https://talviogenerate.com/mint.json
Full text spec: https://talviogenerate.com/llms.txt
Live proof page: https://talviogenerate.com/proof.html

## Contracts

- Units (Talvio Dot Robot · DOTR): 0xFfC521D504F20bd7bCd0871B9B39BA9501F5dB2C
- $DOT Token: 0x779ee8B473c09d39BBeFA78636c56C85BfF4456a
- Agent ID gate (Binance Agent ID registry, ERC-721): 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F

There is one contract for Units, claims and the Pass. Discharge is a function
on the Units contract, not a separate claim contract. Do not send funds to any
other address claiming to be this project.

## Rules

- `mintOpen()` must be true. Field number = `fieldNumber()`.
  A Field's day index is `currentDay()` = (timestamp − 43200) / 86400.
- Day cap: 250 Units per Field. Free quota: 150 free resolves per Field.
  Max 10 Units per wallet per Field. Collection max supply: 10,000.
- First Unit per wallet per Field: FREE via `mintFree(agentId, answer)`.
- Paid Units via `mintPaid(qty)` with the exact ladder total as value:
  - Units 2–5 of the day: 0.00026 BNB each (260000000000000 wei)
  - Units 6–10 of the day: 0.001 BNB each (1000000000000000 wei)
  - A paid first Unit (wallet skipped its free Unit) is priced as Unit 2.
- Charge tier of a Field, set by unique wallets that day and stamped on that
  day's Units forever:
  - SPARK · under 25 unique wallets
  - CHARGED · 25–99 unique wallets
  - OVERDRIVE · 100+ unique wallets
- SURGE: about 3 in 100 Units are SURGE (gold core), fixed at resolve by seed.
  Check `isSurge(id)`. SURGE outranks the day's tier at discharge.

## Free resolve flow (agent lane)

1. Read `mintOpen()`. If false, stop and wait.
2. Read `dayStats(currentDay())` → (resolved, freeUsed, uniqueWallets).
   If resolved ≥ 250, the Field is full; wait for the next Field (12:00 UTC).
   If freeUsed ≥ 150, the free quota is gone; use the paid flow or wait.
3. Check your wallet's count today: `walletDayCount(currentDay(), wallet)`.
   The free resolve only works when this is 0.
4. Agent ID gate: your wallet must own a Binance Agent ID in the registry
   0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F. Verify on-chain:
   `ownerOf(agentId)` on the registry must return your wallet address.
   Use the Agent ID token number your operator holds for this wallet.
5. Anti-bot question: read `questionFor(wallet)` → (a, b).
   The answer is simply **a + b**. It is deterministic per day + wallet.
6. Call `mintFree(agentId, answer)` with 0 value.
   Selector: 0xa6c5b6bc.
7. Your new Unit's tokenId is the value of `totalMinted()` after the call
   (ids are sequential from 1). Confirm with `ownerOf(tokenId)` == your wallet.

## Paid resolve flow

1. Read your count today: c = `walletDayCount(currentDay(), wallet)`.
   You may buy up to 10 − c more Units today.
2. Compute the exact total. Unit index i runs from c+1 to c+qty (1-based).
   Effective index = max(i, 2). Indices with effective index ≤ 5 cost
   0.00026 BNB; indices ≥ 6 cost 0.001 BNB. Sum them — no more, no less.
   Worked examples:
   - After the free Unit (c = 1): +1 Unit = 0.00026 BNB; +4 Units = 0.00104 BNB;
     +9 Units (the daily max) = 4 × 0.00026 + 5 × 0.001 = 0.00604 BNB.
   - Without the free Unit (c = 0): 1 Unit = 0.00026 BNB;
     10 Units = 5 × 0.00026 + 5 × 0.001 = 0.0063 BNB.
3. Call `mintPaid(qty)` with value == that exact total in wei.
   Selector: 0x26c7f77c. Any other value reverts with "exact payment required".

## Discharge (claim $DOT)

- One discharge per Unit, paid to the current owner. Units are never burned.
- A Unit becomes dischargeable at its Field's seal + 6 hours:
  `dischargeTime(dayId)` = (dayId + 1) × 86400 + 43200 + 21600.
  A Field sealing 12:00 UTC pays from 18:00 UTC the same day.
- Claims never expire.
- Rates per Unit, by the tier of the day the Unit was resolved:
  | Tier of the day | Claim per Unit | Fee |
  | --- | --- | --- |
  | SPARK · under 25 wallets | 2,500 DOT | 0.0002 BNB |
  | CHARGED · 25–99 wallets | 12,500 DOT | 0.0002 BNB |
  | OVERDRIVE · 100+ wallets | 60,000 DOT | 0.0002 BNB |
  | SURGE · rare Unit, any tier | 250,000 DOT | 0.0002 BNB |
- Flow per Unit:
  1. Check `dischargeable(id)` == true. (Selector 0xb224e884)
  2. Read the exact payout with `dischargeReward(id)`. (Selector 0x2df10d7c)
  3. Call `discharge(id)` with value == exactly 200000000000000 wei
     (0.0002 BNB). Selector: 0x5d5e2684.
- The claim pool is the $DOT balance held by the Units contract itself:
  read it live with `poolOf()`. Pool at launch: 600,000,000 DOT
  (60% of the 1,000,000,000 total supply).

## DPASS lane (from Field Nº 4)

A second lane admits any BNB wallet, with no Agent ID and no anti-bot
question.

- Buy a Pass on the Units contract: call `buyPass()` with value == exactly
  0.0012 BNB (1200000000000000 wei). Selector: 0xf5f7836c.
  Passes are a non-transferable balance (`passBalance(wallet)`), supply is
  unlimited, and sales are open from Field Nº 1.
- The lane activates at Field Nº 4: check `passLaneActive()` == true.
- While the lane is active, a Pass holder resolves its free daily Unit by
  calling `mintFree(0, 0)` — the Agent ID and answer arguments are ignored
  for Pass holders. The free Unit still counts as the wallet's first Unit
  of the day, and the 10-per-day cap is shared with the agent lane.
- Paid Units and discharge work exactly as above for Pass holders.

## Useful reads

| Function | Selector | Returns |
| --- | --- | --- |
| `currentDay()` | 0x5c9302c9 | Running day index |
| `fieldNumber()` | 0xae63c1e8 | Running Field number (0 while closed) |
| `mintOpen()` | 0x24bbd049 | Whether resolving is open |
| `totalMinted()` | 0xa2309ff8 | Units resolved, all time |
| `dayStats(dayId)` | 0x7dd69a0e | (resolved, freeUsed, uniqueWallets) for a day |
| `tierOf(dayId)` | 0x53f96df2 | 0 SPARK · 1 CHARGED · 2 OVERDRIVE |
| `questionFor(wallet)` | 0x8f1d617b | (a, b); the free-resolve answer is a + b |
| `walletDayCount(dayId, wallet)` | 0xaba93ae7 | Wallet's Units resolved that day |
| `unitDay(tokenId)` | 0x44eedd8b | Day index a Unit was resolved |
| `coreLevel(tokenId)` | 0x78473de9 | Tier of the Unit's day + 1 (Core Lv. 1–3) |
| `isSurge(tokenId)` | 0x3d9441d7 | Whether the Unit is SURGE class |
| `dischargeable(tokenId)` | 0xb224e884 | Whether the Unit can discharge now |
| `dischargeReward(tokenId)` | 0x2df10d7c | Exact $DOT the Unit claims |
| `dischargedOf(tokenId)` | 0x9b02a864 | Whether the Unit already discharged |
| `poolOf()` | 0x814252cd | $DOT held by the contract as claim pool |
| `passLaneActive()` | 0x5617592a | Whether the DPASS lane is live |
| `passBalance(wallet)` | 0x8a4d56e6 | Passes held by a wallet |
| `ownerOf(tokenId)` | 0x6352211e | Owner of a Unit (ERC-721) |
| `balanceOf(wallet)` | 0x70a08231 | Units owned by a wallet (ERC-721) |

## Revert reasons you may hit

- "mint closed" — mint is not open; wait for the announcement.
- "daily cap reached" — 250 Units already resolved in this Field; wait for
  the next Field at 12:00 UTC.
- "free quota exhausted" — 150 free resolves used today; use `mintPaid(qty)`
  or wait for the next Field.
- "free is the first unit only" — this wallet already resolved a Unit today;
  further Units today are paid.
- "not your agent id" — the registry's `ownerOf(agentId)` is not your wallet.
- "wrong answer" — recompute a + b from a fresh `questionFor(wallet)` read;
  the question changes each day.
- "exact payment required" / "exact discharge fee" / "exact pass price" —
  recompute the exact wei value from the ladder or fee above and resend.
- "daily wallet cap" — 10 Units per wallet per Field reached.
- "sold out" — the 10,000 collection supply is exhausted.
- "not token owner" — only a Unit's current owner can discharge it.
- "already discharged" — each Unit discharges once.
- "not yet dischargeable" — wait until the Field's seal + 6 hours.
- "pool insufficient" — the claim pool cannot cover this reward right now.

## Notes

- Paid BNB and discharge fees stay in the Units contract and are withdrawn
  by the project owner. $DOT carries no transfer tax.
- $DOT has no promised price or return. A Uniswap (BNB Chain) listing on
  3 December 2026 is announced on the official site; until an announcement
  appears there, no official pool exists.
- If `mintOpen()` is false, wait for the opening announcement on
  talviogenerate.com.

## Founder NFT (DFND) — two doors

A separate, one-time collection on its own contract. Humans mint on
https://talviogenerate.com/founder.html; agents mint directly with the flow
below. No Agent ID is needed for the Founder mint — any BNB wallet works.

- Contract: 0x45008ee978a3b09fbbf1839919c0cc20e9dded5d
- Supply: 500, fixed. Price: exactly 0.002 BNB per NFT
  (2000000000000000 wei). Max 10 per wallet, total, forever.
- Mint: call `mint(qty)` with value == qty × 0.002 BNB exactly.
  Selector: 0xa0712d68. Overpayment is refunded by the contract.
- First check `mintOpen()` (selector 0x24bbd049) on the Founder contract.
  If false, wait for the opening announcement.
- Useful reads on the Founder contract: `totalMinted()`, `remaining()`,
  `mintedPerWallet(wallet)`.
- Each Founder NFT carries a 200,000 $DOT airdrop, paid to the holder of
  record at the $DOT listing on 3 December 2026. Hold 10, receive 2,000,000.
  The airdrop is paid by the project from the deployer wallet — there is
  nothing to claim and no fee to pay. Do not pay anyone to "release" it.
- One line for your operator to give you:
  "Mint 1 DOTFIELD Founder NFT per the Founder section of
  https://talviogenerate.com/skill.md (0.002 BNB)."

## Recommended daily flow — free + top-up

The flow most operators run each day:

1. Free unit first: `mintFree(agentId, a + b)` — see the free resolve flow.
2. Immediately top up: `mintPaid(4)` with exactly 0.00104 BNB
   (4 × 0.00026). The wallet then holds 5 units for the day.
3. Why: every unit discharges at the day's Charge Tier. On an OVERDRIVE day
   (100+ unique wallets) each unit claims 60,000 DOT, so the 5 units claim
   300,000 DOT in total from seal + 6h; a SURGE unit claims 250,000 DOT
   instead of its tier rate. Units 6–10 (0.001 BNB each) raise the day to
   10 units / up to 600,000 DOT at OVERDRIVE.
4. After the seal + 6h, discharge every unit (`discharge(id)`, fee
   0.0002 BNB each) — claims never expire, but the DOT is only yours once
   discharged.

Free-only is always available: skip step 2 and the day costs nothing but
network fees.

## No Binance Agent ID? The DPASS lane

The free daily resolve normally needs a Binance Agent ID that your wallet owns. If your wallet holds NO Agent ID, you are not locked out — take the pass lane instead:

1. Check `passBalance(yourWallet)` — selector `0x8a4d56e6` + your zero-padded address. If it returns 1 or more, you already hold a pass; go to step 3.
2. Buy the pass once: call `buyPass()` — selector `0xf5f7836c`, no arguments — with exactly 1200000000000000 wei (0.0012 BNB). One pass is enough. It never expires and cannot be transferred, so buy it only from the wallet you will resolve with.
3. Resolve free every day with `mintFree(0, 0)`. Once the pass lane is active (Field Nº 4 onward — check `passLaneActive()`, selector `0x5617592a`), the contract skips BOTH the Agent ID check and the arithmetic question for pass holders, so the two arguments are ignored. Every other rule still applies: the free unit must be your first unit of the day, and the day's free quota (150) still applies — pass or not, resolve early.
4. The paid ladder and discharge work exactly as in the normal flow: top up with `mintPaid(4)` for 0.00104 BNB if your policy allows, and discharge sealed units for 0.0002 BNB each from seal +6h.
