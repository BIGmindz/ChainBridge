#!/bin/bash
#
# New Listings Radar Setup and Test Script
# This script provides a quick way to set up and test the New Listings Radar module
#

# Text formatting
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

echo -e "${BOLD}${BLUE}=======================================${RESET}"
echo -e "${BOLD}${BLUE}   New Listings Radar Setup Script     ${RESET}"
echo -e "${BOLD}${BLUE}=======================================${RESET}"
echo

# Check for Python 3
echo -e "${BOLD}Checking Python version...${RESET}"
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓ Python found: ${PYTHON_VERSION}${RESET}"
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.8 or higher.${RESET}"
    exit 1
fi

# Check for virtual environment
echo -e "\n${BOLD}Checking for virtual environment...${RESET}"
if [[ -d ".venv" || -d "venv" ]]; then
    echo -e "${GREEN}✓ Virtual environment found.${RESET}"
    
    # Activate the virtual environment
    if [[ -d ".venv" ]]; then
        echo -e "Activating .venv environment..."
        source .venv/bin/activate
    elif [[ -d "venv" ]]; then
        echo -e "Activating venv environment..."
        source venv/bin/activate
    fi
else
    echo -e "${YELLOW}⚠ No virtual environment found. Using system Python.${RESET}"
    echo -e "${YELLOW}⚠ Consider creating a virtual environment:${RESET}"
    echo -e "   ${BOLD}python3 -m venv .venv && source .venv/bin/activate${RESET}"
fi

# Run dependency setup
echo -e "\n${BOLD}Setting up dependencies...${RESET}"
python3 setup_new_listings.py

# Check module files exist
echo -e "\n${BOLD}Checking module files...${RESET}"

if [[ -f "modules/new_listings_radar_module.py" ]]; then
    echo -e "${GREEN}✓ Module file found: modules/new_listings_radar_module.py${RESET}"
else
    echo -e "${RED}✗ Module file missing: modules/new_listings_radar_module.py${RESET}"
    echo -e "  Please ensure the module file exists in the correct location."
    exit 1
fi

if [[ -f "new_listings_dashboard.py" ]]; then
    echo -e "${GREEN}✓ Dashboard file found: new_listings_dashboard.py${RESET}"
else
    echo -e "${YELLOW}⚠ Dashboard file missing: new_listings_dashboard.py${RESET}"
fi

# Menu for next actions
echo -e "\n${BOLD}${BLUE}=======================================${RESET}"
echo -e "${BOLD}${BLUE}   Setup Complete! What's next?        ${RESET}"
echo -e "${BOLD}${BLUE}=======================================${RESET}"
echo -e "
${BOLD}1)${RESET} Run test suite
${BOLD}2)${RESET} Scan for new listings now
${BOLD}3)${RESET} Run backtest (last 30 days)
${BOLD}4)${RESET} Launch dashboard
${BOLD}5)${RESET} Exit
"

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo -e "\n${BOLD}Running test suite...${RESET}"
        python3 test_new_listings_radar.py
        ;;
    2)
        echo -e "\n${BOLD}Scanning for new listings...${RESET}"
        python3 run_new_listings_radar.py --scan --save
        ;;
    3)
        echo -e "\n${BOLD}Running backtest over 30 days...${RESET}"
        python3 run_new_listings_radar.py --backtest --days 30 --save
        ;;
    4)
        echo -e "\n${BOLD}Launching dashboard...${RESET}"
        python3 new_listings_dashboard.py
        ;;
    5)
        echo -e "\n${BOLD}Exiting. All set up!${RESET}"
        ;;
    *)
        echo -e "\n${RED}Invalid choice. Exiting.${RESET}"
        ;;
esac

echo -e "\n${BOLD}${GREEN}New Listings Radar is ready to use!${RESET}"
echo -e "See ${BOLD}README_NEW_LISTINGS.md${RESET} and ${BOLD}QUICKSTART_NEW_LISTINGS.md${RESET} for more information."