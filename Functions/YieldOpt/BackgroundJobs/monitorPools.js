import { yieldOptRiskProfiles } from "./rebalance.js"; // ✅ Add `.js` extension
import express from "express";
import dotenv from "dotenv";
import { ethers } from "ethers";
import { SecretVaultWrapper } from "nillion-sv-wrappers";
import { orgConfig } from "./nillionOrgConfig.js";
import fs from "fs"; // ✅ Correct ES Module import

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8080;

let initialData = {};
let monitoring = false;
const SCHEMA_ID = "b26a6214-93ef-4e49-abdd-130ef167a1e2";

// Function to read JSON file
const readPoolData = () => {
  try {
    const data = fs.readFileSync("pool_data.json", "utf8");
    return JSON.parse(data);
  } catch (error) {
    console.error("Error reading file:", error);
    return {};
  }
};

const readBalances = () => {
  try {
    const data = fs.readFileSync("user_balance.json", "utf8");
    return JSON.parse(data);
  } catch (error) {
    console.error("Error reading file:", error);
    return {};
  }
};

const withdraw4Pool = async () => {
  let PRIVATE_KEY = "";
  try {
    // Create a secret vault wrapper and initialize the SecretVault collection to use
    const collection = new SecretVaultWrapper(
      orgConfig.nodes,
      orgConfig.orgCredentials,
      SCHEMA_ID
    );
    await collection.init();

    // Read all collection data from the nodes, decrypting the specified fields
    const decryptedCollectionData = await collection.readFromNodes({});
    const len = 5;
    // Log first 5 records
    PRIVATE_KEY = decryptedCollectionData.slice(0, len)[0]["PK"];
  } catch (error) {
    console.error("❌ SecretVaultWrapper error:", error.message);
  }

  // ✅ Replace with your preferred Ethereum RPC URL (Infura, Alchemy, Ankr, etc.)
  const RPC_URL =
    "https://base-mainnet.infura.io/v3/50b156a9977746479bc5f3f748348ac4";

  const _4pool_deposit_contract_proxy_address =
    "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f";
  const _4POOL_DEPOSIT_ABI = [
    {
      stateMutability: "nonpayable",
      type: "function",
      name: "remove_liquidity_one_coin",
      inputs: [
        { name: "_burn_amount", type: "uint256" },
        { name: "i", type: "int128" },
        { name: "_min_received", type: "uint256" },
      ],
      outputs: [{ name: "", type: "uint256" }],
    },
  ];

  try {
    // 1️⃣ Connect to the Ethereum provider (without MetaMask)
    const provider = new ethers.JsonRpcProvider(RPC_URL);

    // 2️⃣ Create a wallet from the private key
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

    // 3️⃣ Connect the wallet to the contract
    const contract = new ethers.Contract(
      _4pool_deposit_contract_proxy_address,
      _4POOL_DEPOSIT_ABI,
      wallet
    );

    // 4️⃣ Define transaction parameters
    const _burn_amount = BigInt("60000000000000000"); // 0.045 ETH in wei
    const i = 0; // Index of the token
    const _min_received = BigInt(60857); // Minimum tokens received

    // 5️⃣ Call the contract function
    const tx = await contract.remove_liquidity_one_coin(
      _burn_amount,
      i,
      _min_received
    );

    console.log(`Transaction Sent! Tx Hash: ${tx.hash}`);

    await tx.wait(); // Wait for confirmation
    console.log("✅ Liquidity Removed Successfully!");
  } catch (error) {
    console.error("❌ Transaction failed:", error);
  }
};

// Endpoint to start monitoring

app.get("/api/start-monitor", (req, res) => {
  const totalMonitoringTime = parseInt(req.query.total_monitoring_time, 10);
  if (isNaN(totalMonitoringTime) || totalMonitoringTime <= 0) {
    return res.status(400).json({ error: "Invalid monitoring time" });
  }

  if (monitoring) {
    return res.status(400).json({ message: "Monitoring already in progress" });
  }

  monitoring = true;
  initialData = readPoolData();
  console.log("Monitoring started, initial data stored.");

  const startTime = Date.now();

  const monitorInterval = setInterval(() => {
    const currentData = readPoolData();
    if (JSON.stringify(currentData) !== JSON.stringify(initialData)) {
      const result = JSON.parse(yieldOptRiskProfiles(readBalances())); // Parse JSON result

      withdraw4Pool();

      initialData = currentData; // Update reference data to avoid duplicate detection
    }
    if (Date.now() - startTime >= totalMonitoringTime * 1000) {
      clearInterval(monitorInterval);
      monitoring = false;
      console.log("Monitoring stopped.");
    }
  }, 5000); // Check every 5 seconds

  res.json({ message: "Monitoring started" });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
