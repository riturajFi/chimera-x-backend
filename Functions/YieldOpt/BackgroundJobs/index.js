import { SecretVaultWrapper } from "nillion-sv-wrappers";
import { orgConfig } from "./nillionOrgConfig.js";

// Use postSchema.js to create a new collection schema
// Update SCHEMA_ID to the schema id of your new collection
const SCHEMA_ID = "b26a6214-93ef-4e49-abdd-130ef167a1e2";

const data = [
  {
    PK: { $allot: "4733477c5f822194e31cb0a088f911bf9b1d15be6393ed7845c52ed433b01824" }, // will be encrypted to a $share
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

    // Read all collection data from the nodes, decrypting the specified fields
    const decryptedCollectionData = await collection.readFromNodes({});

    // Log first 5 records
    console.log(
      decryptedCollectionData.slice(0, data.length)[0]["PK"]
    );
  } catch (error) {
    console.error("❌ SecretVaultWrapper error:", error.message);
    process.exit(1);
  }
}

main();
