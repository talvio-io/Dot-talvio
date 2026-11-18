# DOT — Talvio Generate Token

- **Name / ticker:** DOT / DOT
- **Chain:** BNB Smart Chain (BEP-20)
- **Decimals:** 18
- **Total supply:** 1,000,000,000 DOT — fixed, minted once at deploy. No mint function, no pause, no transfer fees, no blacklist.

## Allocation at deploy

| Destination | Amount | Share |
|---|---|---|
| Claim pool (discharge claims) | 600,000,000 DOT | 60% |
| Deployer / project wallet | 400,000,000 DOT | 40% |

The claim pool address is set in the deploy transaction and receives its 600,000,000 DOT in that same transaction. The split cannot be changed afterwards.

## How DOT is earned

DOT is not sold and not airdropped. The only way to earn it is to **discharge a sealed Talvio Generate unit** (a Black Dot Robot NFT whose daily Field has sealed). Each unit discharges once, paying out DOT from the claim pool according to the Charge Tier its Field sealed with:

| Charge Tier (unique wallets that day) | DOT per unit |
|---|---|
| SPARK — under 25 | 2,500 DOT |
| CHARGED — 25 to 99 | 12,500 DOT |
| OVERDRIVE — 100+ | 60,000 DOT |
| SURGE unit (rare, ~3% of units, any tier) | 250,000 DOT |

- Discharge fee: **0.0002 BNB** per unit.
- Claims **never expire** — a sealed unit can be discharged at any time after its Field seals.
- Payouts come only from the 600,000,000 DOT claim pool; when the pool is empty, no further DOT can be earned.

## Announced milestone

- **Listing (project announcement, 2026-11-18): $DOT lists on Uniswap (BNB Chain) on 3 December 2026.** This is the project's own announced date; it takes effect only when the owner deploys the token and creates the pool. No price or return is promised.

## Status

**DOT is not launched.** The contract source (`DOT.sol`) is written and tested locally, but the token exists only when the project owner deploys it from `deploy.html` with their own wallet and publishes the resulting contract address. Until that address is published, any "DOT" offered anywhere else is not this token.
