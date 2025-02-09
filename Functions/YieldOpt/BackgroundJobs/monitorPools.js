const { yieldOptRiskProfiles } = require("./rebalance");
const express = require("express");
const fs = require("fs");
const app = express();
const PORT = process.env.PORT || 8080;

let initialData = {};
let monitoring = false;

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
      console.log(result.change);
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
