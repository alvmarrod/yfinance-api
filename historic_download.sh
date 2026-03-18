#!/bin/bash

IBEX_35_SYMBOLS=(
    "ITX.MC"
    "MTS.MC"
    "MAP.MC"
    "FDR.MC"
    "MRL.MC"
    "ACX.MC"
    "PUIG.MC"
    "COL.MC"
    "LOG.MC"
    "NTGY.MC"
    "AMS.MC"
    "TEF.MC"
    "ENG.MC"
    "IAG.MC"
    "BKT.MC"
    "RED.MC"
    "SAN.MC"
    "CLNX.MC"
    "UNI.MC"
    "SAB.MC"
    "IBE.MC"
    "FER.MC"
    "BBVA.MC"
    "GRF.MC"
    "ACS.MC"
    "AENA.MC"
    "ELE.MC"
    "ANA.MC"
    "CABK.MC"
    "ANE.MC"
)

SP_100_SYMBOLS=(
    "AAPL"
    "ABBV"
    "ABT"
    "ACN"
    "ADBE"
    "AIG"
    "AMD"
    "AMGN"
    "AMT"
    "AMZN"
    "AVGO"
    "AXP"
    "BA"
    "BAC"
    "BK"
    "BKNG"
    "BLK"
    "BMY"
    "BRK.B"
    "C"
    "CAT"
    "CHTR"
    "CL"
    "CMCSA"
    "COF"
    "COP"
    "COST"
    "CRM"
    "CSCO"
    "CVS"
    "CVX"
    "DE"
    "DHR"
    "DIS"
    "DUK"
    "EMR"
    "FDX"
    "GD"
    "GE"
)

NIKKEI_225_SYMBOLS=(
    "1332.T"
    "2002.T"
    "2269.T"
    "2282.T"
    "2501.T"
    "2502.T"
    "2503.T"
    "2801.T"
    "2802.T"
    "2871.T"
    "2914.T"
    "3086.T"
    "3092.T"
    "3099.T"
    "3382.T"
    "7453.T"
    "8233.T"
    "8252.T"
    "8267.T"
    "9843.T"
    "9983.T"
    "4151.T"
    "4502.T"
    "4503.T"
    "4506.T"
    "4507.T"
    "4519.T"
    "4523.T"
    "4568.T"
    "4578.T"
    "4543.T"
    "4902.T"
    "6146.T"
    "7731.T"
    "7733.T"
    "7741.T"
    "7762.T"
    "6479.T"
    "6501.T"
    "6503.T"
    "6504.T"
    "6506.T"
    "6526.T"
    "6594.T"
    "6645.T"
    "6674.T"
    "6701.T"
    "6702.T"
    "6723.T"
    "6724.T"
    "6752.T"
    "6753.T"
    "6758.T"
    "6762.T"
    "6770.T"
    "6841.T"
    "6857.T"
    "6861.T"
    "6902.T"
    "6920.T"
    "6952.T"
    "6954.T"
    "6971.T"
    "6976.T"
    "6981.T"
    "7735.T"
    "7751.T"
    "7752.T"
    "8035.T"
    "7201.T"
    "7202.T"
    "7203.T"
    "7205.T"
    "7211.T"
    "7261.T"
    "7267.T"
    "7269.T"
    "7270.T"
    "7272.T"
    "5831.T"
    "7186.T"
    "8304.T"
    "8306.T"
    "8308.T"
    "8309.T"
    "8316.T"
    "8331.T"
    "8354.T"
    "8411.T"
    "8253.T"
    "8591.T"
    "8697.T"
    "8601.T"
    "8604.T"
    "8630.T"
    "8725.T"
    "8750.T"
    "8766.T"
    "8795.T"
    "9432.T"
    "9433.T"
    "9434.T"
    "9613.T"
    "9984.T"
    "3289.T"
    "8801.T"
    "8802.T"
    "8804.T"
    "8830.T"
    "9001.T"
    "9005.T"
    "9007.T"
    "9008.T"
    "9009.T"
    "9020.T"
    "9021.T"
    "9022.T"
    "9064.T"
    "9147.T"
    "9101.T"
    "9104.T"
    "9107.T"
    "9201.T"
    "9202.T"
    "9501.T"
    "9502.T"
    "9503.T"
    "9531.T"
    "9532.T"
)

EUROSTOXX50_SYMBOLS=(
  "ADS.F" "ADYEN.F" "AD.F" "AI.F" "AIR.F" "ALV.F" "AMS.F" "ABI.F" "ASML.F" "CS.F"
  "BAS.F" "BAYN.F" "BMW.F" "BNP.F" "CRG.F" "DAI.F" "BN.F" "DB1.F" "DPW.F" "DTE.F"
  "ENEL.F" "ENGI.F" "ENI.F" "EL.F" "FLTR.F" "IBE.F" "ITX.F" "IFX.F" "INGA.F" "ISP.F"
  "KER.F" "KNEBV.F" "OR.F" "LIN.F" "MC.F" "MUV2.F" "NOKIA.F" "RI.F" "ORA.F" "PHIA.F"
  "PRX.F" "SAF.F" "SAN.F" "SAN.F" "SAP.F" "SU.F" "SIE.F" "TEF.F" "FP.F" "DG.F"
  "VIV.F" "VOW.F" "VNA.F"
)

# Define 10 stocks from different sectors (NASDAQ/SP500)
BASIC_USA_SYMBOLS=(
    "MSFT"    # Technology (Microsoft)
    "JNJ"     # Healthcare (Johnson & Johnson)
    "PG"      # Consumer Goods (Procter & Gamble)
    "JPM"     # Financials (JPMorgan Chase)
    "XOM"     # Energy (Exxon Mobil)
    "AMZN"    # Consumer Discretionary (Amazon)
    "GOOGL"   # Communication Services (Alphabet)
    "UNH"     # Healthcare (UnitedHealth Group)
    "HD"      # Industrials (Home Depot)
    "V"       # Financials (Visa)
)

# Combine all symbols into one array, excluding duplicates
SYMBOLS=(
    "${IBEX_35_SYMBOLS[@]}"
    "${SP_100_SYMBOLS[@]}"
    "${NIKKEI_225_SYMBOLS[@]}"
    "${EUROSTOXX50_SYMBOLS[@]}"
    "${BASIC_USA_SYMBOLS[@]}"
)

# Check the number of symbols - Print the count
echo "Total number of symbols: ${#SYMBOLS[@]}"

# Remove duplicates
SYMBOLS=($(printf "%s\n" "${SYMBOLS[@]}" | sort -u))

# Print the number of unique symbols
echo "Number of unique symbols: ${#SYMBOLS[@]}"

# Base URL for the API
BASE_URL="http://localhost:5001/symbol/historic/candle"

# Fetch data for each symbol in parallel
for symbol in "${SYMBOLS[@]}"; do
    echo "Fetching data for $symbol..."
    curl "$BASE_URL/$symbol"
    # Add a sleep to avoid overwhelming the server
    sleep 3
done

echo "Extracting data from container"

#docker exec yfinance_api_instance ls | grep .csv
#docker cp yfinance_api_instance:/python-docker/*.csv ~/github/wallet-agent/data/yfinance/
#docker cp yfinance_api_instance:/python-docker/AMZN_5m_20250320_20250519.csv ~/github/wallet-agent/data/yfinance/

# Configuration
CONTAINER_NAME="yfinance_api_instance"
CONTAINER_PATH="/python-docker"

# Local target directory
# Last part is the date in YYYYMMDD format
TODAY=$(date +%Y%m%d)
LOCAL_TARGET_DIR="$HOME/github/wallet-agent/data/yfinance/${TODAY}/"

# Create target directory if it doesn't exist
mkdir -p "$LOCAL_TARGET_DIR"

# Get list of CSV files from container
echo "Fetching CSV files from container..."
csv_files=$(docker exec "$CONTAINER_NAME" ls "$CONTAINER_PATH" | grep '\.csv$')

# Check if any files were found
if [ -z "$csv_files" ]; then
    echo "No CSV files found in container!"
    exit 1
fi

# Copy each file
echo "Found $(echo "$csv_files" | wc -l) CSV files:"
echo "----------------------------------------"

counter=0
for file in $csv_files; do
    ((counter++))
    echo "[$counter] Copying $file..."
    docker cp "$CONTAINER_NAME:$CONTAINER_PATH/$file" "$LOCAL_TARGET_DIR/"
    
    # Verify copy was successful
    if [ -f "$LOCAL_TARGET_DIR/$file" ]; then
        echo "    ✓ Successfully copied to $LOCAL_TARGET_DIR/$file"
    else
        echo "    ✗ Failed to copy $file!"
    fi
done

echo "----------------------------------------"
echo "Copied $counter files to $LOCAL_TARGET_DIR"

echo "All data fetched!"
