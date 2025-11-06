{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python with required packages
    (python312.withPackages (ps: with ps; [
      gspread
      google-auth-oauthlib
      requests
      websocket-client  # For WebSocket exploration
    ]))

    # Utilities
    sqlite  # For cookie extraction
  ];

  shellHook = ''
    echo "NCL Sheet Sync"
    echo "=============="
    echo ""
    echo "Python version: $(python --version)"
    echo ""
    echo "Available packages:"
    echo "  - gspread (Google Sheets API)"
    echo "  - google-auth-oauthlib (OAuth2 authentication)"
    echo "  - requests (HTTP client)"
    echo ""
    echo "Quick start:"
    echo "  1. cp config.example.py config.py"
    echo "  2. Edit config.py with your values"
    echo "  3. ./utils/setup_google_auth.py (if needed)"
    echo "  4. ./update_sheet.py osint --test --yes"
    echo ""
    echo "For help: ./update_sheet.py --help"
    echo ""
  '';
}
