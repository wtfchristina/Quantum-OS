import argparse
import sys
from quantumcore import QuantumCoreClient

def main():
    parser = argparse.ArgumentParser(description="QuantumCore CLI Gateway")
    subparsers = parser.add_subparsers(dest="command")

    # Command: limits
    subparsers.add_parser("limits", help="Query vault spending limits and hourly status")

    # Command: pay
    pay_parser = subparsers.add_parser("pay", help="Execute an autonomous guarded transaction")
    pay_parser.add_argument("recipient", type=str, help="Recipient Ethereum address")
    pay_parser.add_argument("amount", type=float, help="Amount in USD (capped at $5.00)")

    args = parser.parse_args()
    client = QuantumCoreClient()

    if args.command == "limits":
        limits = client.get_limits()
        print("--- QuantumCore Vault Limits ---")
        print(f"Max Per Tx   : ${limits['max_per_tx']:.2f}")
        print(f"Hourly Cap   : ${limits['hourly_cap']:.2f}")
        print(f"Spent Hour   : ${limits['spent_this_hour']:.2f}")

    elif args.command == "pay":
        print(f"Submitting payment of ${args.amount:.2f} to {args.recipient}...")
        try:
            res = client.pay(args.recipient, args.amount)
            print("[SUCCESS] Payment settled on Sepolia!")
            print(f"Block Number : #{res['block_number']}")
            print(f"Explorer URL : {res['explorer_url']}")
        except Exception as e:
            print(f"[REJECTED] {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
