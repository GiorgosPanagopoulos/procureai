// Create the RAG vector index on the local mongodb-atlas-local container.
//
// Run by the mongo-init service in docker-compose.yml on every `docker compose up`.
// Reads the same definition used for Atlas (backend/rag/atlas_vector_index.json),
// creates it only if it is missing, then waits until it is queryable so the
// backend never starts against an index that is still building.

const fs = require("fs");

const spec = JSON.parse(fs.readFileSync("/init/atlas_vector_index.json", "utf8"));
const target = db.getSiblingDB(spec.database);

// createSearchIndex needs the collection to exist.
if (!target.getCollectionNames().includes(spec.collectionName)) {
  target.createCollection(spec.collectionName);
}
const coll = target.getCollection(spec.collectionName);
const ns = `${spec.database}.${spec.collectionName}`;

if (coll.getSearchIndexes(spec.name).length) {
  print(`${spec.name} on ${ns} already exists`);
} else {
  coll.createSearchIndex(spec.name, spec.type, spec.definition);
  print(`Created ${spec.name} on ${ns}`);
}

const deadline = Date.now() + 120 * 1000;
for (;;) {
  const [index] = coll.getSearchIndexes(spec.name);
  if (index && index.queryable) {
    print(`${spec.name} is ${index.status}`);
    break;
  }
  if (Date.now() > deadline) {
    print(`${spec.name} not queryable after 120s (status: ${index && index.status})`);
    quit(1);
  }
  sleep(2000);
}
