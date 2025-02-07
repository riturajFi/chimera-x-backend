import { SecretVaultWrapper } from "nillion-sv-wrappers";
import { orgConfig } from "./nillionOrgConfig.js";

// Use postSchema.js to create a new collection schema
// Update SCHEMA_ID to the schema id of your new collection
const SCHEMA_ID = "071a8a78-56b3-49e0-bad4-e606eb1f2915";

const data = [
  {
    name: { $allot: "Vitalik Buterin" }, // will be encrypted to a $share
    years_in_web3: { $allot: 8 }, // will be encrypted to a $share
    responses: [
      { rating: 5, question_number: 1 },
      { rating: 3, question_number: 2 },
    ],
  },
  {
    name: { $allot: "Satoshi Nakamoto" }, // will be encrypted to a $share
    years_in_web3: { $allot: 14 }, // will be encrypted to a $share
    responses: [
      { rating: 2, question_number: 1 },
      { rating: 5, question_number: 2 },
    ],
  },
];

async function main() {
  try {
    // Create a secret vault wrapper and initialize the SecretVault collection to use
    const collection = new SecretVaultWrapper(
      orgConfig.nodes,
      orgConfig.orgCredentials,
      SCHEMA_ID
    );
    await collection.init();

    // Write collection data to nodes encrypting the specified fields ahead of time
    const dataWritten = await collection.writeToNodes(data);
    console.log(
      "👀 Data written to nodes:",
      JSON.stringify(dataWritten, null, 2)
    );

    // Get the ids of the SecretVault records created
    const newIds = [
      ...new Set(dataWritten.map((item) => item.result.data.created).flat()),
    ];
    console.log("uploaded record ids:", newIds);

    // Read all collection data from the nodes, decrypting the specified fields
    const decryptedCollectionData = await collection.readFromNodes({});

    // Log first 5 records
    console.log(
      "Most recent records",
      decryptedCollectionData.slice(0, data.length)
    );
  } catch (error) {
    console.error("❌ SecretVaultWrapper error:", error.message);
    process.exit(1);
  }
}

main();
