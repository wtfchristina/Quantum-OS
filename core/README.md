# QuantumCore (quantumcore.cloud)

> Tokenized, programmable financial core and intent-routing layer with smart contract security guardrails for autonomous AI agents.

[![Network](https://img.shields.io/badge/Network-Ethereum_Sepolia-blue)](https://sepolia.etherscan.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

QuantumCore provides deterministic financial execution rails and risk limits for autonomous LLM agents (CrewAI, AutoGen, LangChain). It enables agents to disburse micro-payments and settle on-chain invoices while enforcing programmatic caps at the smart contract level to prevent rogue spends or prompt-injection fund drains.

---

## 1. Network & Deployments (Ethereum Sepolia)

The core settlement engine and digital test currency are deployed and verified on **Ethereum Sepolia**:

| Contract | Address | Verification |
| :--- | :--- | :--- |
| **QuantumVault** | `0x82A11A9e65B927B0652A84b331EAeDBa6D11d6f0` | [View on Etherscan](https://sepolia.etherscan.io/address/0x82A11A9e65B927B0652A84b331EAeDBa6D11d6f0) |
| **TestUSD (`qUSD`)** | `0x2E7cf43296Fe3a157c9C28c011629bd0BA0A307E` | [View on Etherscan](https://sepolia.etherscan.io/address/0x2E7cf43296Fe3a157c9C28c011629bd0BA0A307E) |

### On-Chain Guardrail Policy
* **Single Transaction Cap:** `$5.00` (Enforced on-chain via `maxPerTx`)
* **Rolling Hourly Limit:** `$20.00` (Enforced on-chain via `hourlyCap` and `spentThisHour`)
* **Settlement Precision:** 6-decimal digital dollar (`qUSD`)

---

## 2. Installation & Quickstart

```bash
git clone [https://github.com/wtfchristina/quantumcore.git](https://github.com/wtfchristina/quantumcore.git)
cd quantumcore
pip install -e .
---

## Platforms & Links
* 🌐 **Web Platform:** [quantumcore.cloud](https://www.quantumcore.cloud)
* 💼 **Author:** [Christina Holt](https://www.linkedin.com/in/YOUR-LINKEDIN-USERNAME)
* 📜 **Smart Contract:** [Sepolia Etherscan](https://sepolia.etherscan.io/address/0x82A11A9e65B927B0652A84b331EAeDBa6D11d6f0)
