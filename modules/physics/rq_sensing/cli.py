import argparse
import json
from pathlib import Path
import numpy as np
from .core import Spectrum, estimate_field

def main():
    parser = argparse.ArgumentParser(description='Fit a single raw-count ODMR scan')
    parser.add_argument('csv', type=Path, help='CSV with frequency_mhz,counts columns')
    parser.add_argument('--dwell-s', type=float, required=True)
    parser.add_argument('--strain-mhz', type=float, default=.15)
    parser.add_argument('--output', type=Path, default=Path('estimate.json'))
    args = parser.parse_args()
    try:
        data = np.genfromtxt(args.csv, delimiter=',', names=True)
        spectrum = Spectrum(data['frequency_mhz'], data['counts'], args.dwell_s)
        estimate = estimate_field(spectrum, args.strain_mhz)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(estimate.to_dict(), indent=2, allow_nan=False))
        print(json.dumps(estimate.to_dict(), indent=2, allow_nan=False))
    except (ValueError, KeyError, OSError, IndexError) as exc:
        parser.exit(2, f'Input error: {exc}\n')
    return 0 if estimate.accepted else 3

if __name__ == '__main__':
    raise SystemExit(main())
