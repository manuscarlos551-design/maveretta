#!/bin/bash

# Initialize MongoDB replica set
echo "Initializing MongoDB replica set..."

# Wait for MongoDB to start
sleep 10

# Initialize replica set
mongosh --eval "
rs.initiate({
  _id: 'rs0',
  members: [
    { _id: 0, host: 'mongodb:27017' }
  ]
});
"

# Create database and collections
mongosh --eval "
use maveretta_db;

// Create collections
db.createCollection('trades');
db.createCollection('signals');
db.createCollection('metrics');
db.createCollection('bot_status');

// Insert sample data
db.trades.insertMany([
  {
    id: '1',
    symbol: 'BTCUSDT',
    side: 'BUY',
    quantity: 0.01,
    price: 45000,
    status: 'completed',
    timestamp: new Date()
  },
  {
    id: '2',
    symbol: 'ETHUSDT',
    side: 'SELL',
    quantity: 0.1,
    price: 3000,
    status: 'active',
    timestamp: new Date()
  }
]);

db.bot_status.insertOne({
  id: 'maveretta_bot',
  status: 'active',
  consecutive_losses: 0,
  max_losses: 5,
  symbol_status: 'LIVRE',
  session_status: 'ATIVA',
  last_update: new Date()
});

console.log('Database initialized successfully');
"

echo "MongoDB initialization completed"