import requests
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Set reference faces for a wedding.")
    parser.add_argument("slug", help="The wedding slug")
    parser.add_argument("--bride", help="Path to the bride's reference photo")
    parser.add_argument("--groom", help="Path to the groom's reference photo")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the backend")
    
    args = parser.parse_args()
    
    if not args.bride and not args.groom:
        print("Please provide at least one of --bride or --groom")
        sys.exit(1)
        
    set_reference_url = f"{args.url}/api/weddings/{args.slug}/set_reference/"
    
    if args.bride:
        print(f"Setting bride reference using {args.bride}...")
        with open(args.bride, 'rb') as f:
            files = {'file': f}
            data = {'role': 'bride'}
            response = requests.post(set_reference_url, files=files, data=data)
            print(f"Response: {response.status_code}")
            print(response.json())
            
    if args.groom:
        print(f"Setting groom reference using {args.groom}...")
        with open(args.groom, 'rb') as f:
            files = {'file': f}
            data = {'role': 'groom'}
            response = requests.post(set_reference_url, files=files, data=data)
            print(f"Response: {response.status_code}")
            print(response.json())

if __name__ == "__main__":
    main()
