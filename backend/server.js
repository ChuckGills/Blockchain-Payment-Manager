// server.js - Express backend to handle Midnight wallet operations
const express = require('express');
const bodyParser = require('body-parser');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');


const MAX_SAFE_TRANSACTION = 100000000;
// We'll load the ES modules dynamically
let WalletBuilder, NetworkId, nativeToken, SmartContract;

const app = express();
app.use(bodyParser.json());

// Config
const INDEXER_URL = 'https://indexer.testnet-02.midnight.network/api/v1/graphql';
const INDEXER_WS_URL = 'wss://indexer.testnet-02.midnight.network/api/v1/graphql';
const PROVING_SERVER_URL = 'http://localhost:6300'; 
const NODE_URL = 'https://rpc.testnet-02.midnight.network';

const walletStore = {};
const escrowStore = {};

// Initialize the modules asynchronously
async function initModules() {
  const walletModule = await import('@midnight-ntwrk/wallet');
  const zswapModule = await import('@midnight-ntwrk/zswap');
  
  try {
    const contractModule = await import('@midnight-ntwrk/contract');
    SmartContract = contractModule.SmartContract;
    console.log('Midnight contract module loaded successfully');
  } catch (error) {
    console.error('Failed to load contract module:', error);
  }
  
  WalletBuilder = walletModule.WalletBuilder;
  NetworkId = zswapModule.NetworkId;
  nativeToken = zswapModule.nativeToken;
  
  console.log('Midnight wallet modules loaded successfully');
}


function loadReportedAddresses() {
    try {
      const reportedData = fs.readFileSync(path.join(__dirname, 'data/reported.txt'), 'utf8');
      // Split the file by lines and remove any empty lines
      return reportedData.split('\n').filter(line => line.trim() !== '');
    } catch (error) {
      console.error('Error loading reported addresses:', error);
      // Return empty array if file doesn't exist or has other issues
      return [];
    }}
// Initialize the server after modules are loaded
async function startServer() {
  try {
    await initModules();
    
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
      console.log(`Midnight wallet server running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to initialize server:', error);
    process.exit(1);
  }
}

app.post('/create-wallet', async (req, res) => {
  try {
    const wallet = await WalletBuilder.build(
      INDEXER_URL,
      INDEXER_WS_URL,
      PROVING_SERVER_URL,
      NODE_URL,
      NetworkId.TestNet,
      'error' 
    );
    
    wallet.start();
    
    // Get wallet address
    let address;
    const subscription = wallet.state().subscribe((state) => {
      address = state.address;
      subscription.unsubscribe();
     
      const walletId = Math.random().toString(36).substring(2, 15);
      walletStore[walletId] = wallet;
      
      res.json({
        status: 'success',
        address: address,
        walletId: walletId
      });
    });
    
  } catch (error) {
    console.error('Error creating wallet:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.post('/connect-wallet-seed', async (req, res) => {
  try {
    const { seed } = req.body;
    
    if (!seed) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Seed is required' 
      });
    }
    
    const wallet = await WalletBuilder.buildFromSeed(
      INDEXER_URL,
      INDEXER_WS_URL,
      PROVING_SERVER_URL,
      NODE_URL,
      seed,
      NetworkId.TestNet,
      'error'
    );
    
    wallet.start();
    
    let address;
    const subscription = wallet.state().subscribe((state) => {
      address = state.address;
      subscription.unsubscribe();
      
      const walletId = Math.random().toString(36).substring(2, 15);
      walletStore[walletId] = wallet;
      
      res.json({
        status: 'success',
        address: address,
        walletId: walletId
      });
    });
    
  } catch (error) {
    console.error('Error connecting wallet with seed:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.post('/restore-wallet', async (req, res) => {
  try {
    const { snapshot } = req.body;
    
    if (!snapshot) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Snapshot is required' 
      });
    }
    
    const wallet = await WalletBuilder.restore(
      INDEXER_URL,
      INDEXER_WS_URL,
      PROVING_SERVER_URL,
      NODE_URL,
      snapshot,
      'error' 
    );
    
    wallet.start();
    
    let address;
    const subscription = wallet.state().subscribe((state) => {
      address = state.address;
      subscription.unsubscribe();
      
      const walletId = Math.random().toString(36).substring(2, 15);
      walletStore[walletId] = wallet;
      
      res.json({
        status: 'success',
        address: address,
        walletId: walletId
      });
    });
    
  } catch (error) {
    console.error('Error restoring wallet:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.get('/get-balance', async (req, res) => {
  try {
    const { walletId } = req.query;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    
    const subscription = wallet.state().subscribe((state) => {
      const tDustToken = nativeToken();
      const balance = state.balances[tDustToken] || 0n;
      
      subscription.unsubscribe();
      
      res.json({
        status: 'success',
        balance: balance.toString(),
        address: state.address
      });
    });
    
  } catch (error) {
    console.error('Error getting balance:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.post('/send-transaction', async (req, res) => {
    try {
      const { walletId, receiverAddress, amount, memo, bypassWarning } = req.body;
      
      if (!walletId || !walletStore[walletId]) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Invalid wallet ID' 
        });
      }
      
      if (!receiverAddress) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Receiver address is required' 
        });
      }
      
      if (!amount || isNaN(Number(amount))) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Valid amount is required' 
        });
      }
  
      // Safety checks
      const reportedAddresses = loadReportedAddresses();
      const isAddressReported = reportedAddresses.includes(receiverAddress);
      const isAmountAboveThreshold = BigInt(amount) > BigInt(MAX_SAFE_TRANSACTION);
      
      // If address is reported or amount is above threshold and bypassWarning isn't true
      if ((isAddressReported || isAmountAboveThreshold) && !bypassWarning) {
        let warningMessage = '';
        
        if (isAddressReported) {
          warningMessage += 'This address has been reported for suspicious activity. ';
        }
        
        if (isAmountAboveThreshold) {
          warningMessage += `This transaction amount (${parseInt(amount)/1_000_000} tDUST) exceeds the recommended safe limit of ${MAX_SAFE_TRANSACTION/1_000_000} tDUST. `;
        }
        
        warningMessage += 'Are you sure you want to proceed?';
        
        return res.status(400).json({
          status: 'warning',
          message: warningMessage,
          requiresConfirmation: true
        });
      }
      
      const wallet = walletStore[walletId];
      
      const transferRecipe = await wallet.transferTransaction([
        {
          amount: BigInt(amount),
          receiverAddress: receiverAddress,
          type: nativeToken() 
        }
      ]);
      
      const provenTransaction = await wallet.proveTransaction(transferRecipe);
      
      const submittedTransaction = await wallet.submitTransaction(provenTransaction);
      
      res.json({
        status: 'success',
        transactionHash: submittedTransaction.hash,
        message: 'Transaction submitted successfully'
      });
      
    } catch (error) {
      console.error('Error sending transaction:', error);
      res.status(500).json({ 
        status: 'error', 
        message: error.message 
      });
    }
  });
app.get('/create-snapshot', async (req, res) => {
  try {
    const { walletId } = req.query;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    const serializedState = await wallet.serialize();
    
    res.json({
      status: 'success',
      snapshot: serializedState
    });
    
  } catch (error) {
    console.error('Error creating snapshot:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.post('/close-wallet', async (req, res) => {
  try {
    const { walletId } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    await wallet.close();
    
    delete walletStore[walletId];
    
    res.json({
      status: 'success',
      message: 'Wallet closed successfully'
    });
    
  } catch (error) {
    console.error('Error closing wallet:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Begin Escrow endpoints
// Create an escrow with approval functionality
app.post('/create-escrow', async (req, res) => {
  try {
    const { walletId, receiverAddress, amount, memo, arbiterAddress } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!receiverAddress) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Receiver address is required' 
      });
    }
    
    if (!amount || isNaN(Number(amount))) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Valid amount is required' 
      });
    }
    
    const wallet = walletStore[walletId];
    
    // Get wallet address
    let senderAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        senderAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    // Create escrow ID
    const escrowId = uuidv4();
    
    // Prepare escrow parameters
    const escrowParams = {
      buyer: senderAddress,  // Buyer/sender
      seller: receiverAddress, // Seller/receiver
      amount: amount,
      memo: memo || '',
      // Default values for contract state
      buyerApproved: false,
      sellerApproved: false,
      fundsReleased: false,
      disputeRaised: false
    };
    
    // Add arbiter if provided
    if (arbiterAddress) {
      escrowParams.arbiter = arbiterAddress;
    }
    
    console.log(`Creating escrow contract for: ${senderAddress} -> ${receiverAddress}, amount: ${amount}`);
    

    
    // For now, simulate contract deployment
    const contractAddress = 'mid1' + crypto.randomBytes(20).toString('hex');
    const transactionHash = 'txhash_' + crypto.randomBytes(32).toString('hex');
    
    // Store escrow details
    escrowStore[escrowId] = {
      id: escrowId,
      ...escrowParams,
      contractAddress: contractAddress,
      transactionHash: transactionHash,
      createdAt: new Date().toISOString(),
      status: 'Active'
    };
    
    res.json({
      status: 'success',
      escrowId: escrowId,
      contractAddress: contractAddress,
      transactionHash: transactionHash,
      message: 'Escrow created successfully'
    });
    
  } catch (error) {
    console.error('Error creating escrow:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Get escrows for a user based on their role
app.get('/get-escrows', async (req, res) => {
  try {
    const { walletId, role } = req.query;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!role || !['buyer', 'seller', 'arbiter'].includes(role)) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Valid role is required (buyer, seller, or arbiter)' 
      });
    }
    
    const wallet = walletStore[walletId];
    
    // Get wallet address
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    // Find all escrows where user has the specified role
    const roleField = role;  // 'buyer', 'seller', or 'arbiter'
    
    const userEscrows = Object.values(escrowStore).filter(
      escrow => escrow[roleField] === userAddress
    );
    
  
    
    res.json({
      status: 'success',
      escrows: userEscrows
    });
    
  } catch (error) {
    console.error('Error getting escrows:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Approve an escrow (as buyer or seller)
app.post('/approve-escrow', async (req, res) => {
  try {
    const { walletId, escrowId, role } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!escrowId || !escrowStore[escrowId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid escrow ID' 
      });
    }
    
    if (!role || !['buyer', 'seller'].includes(role)) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Valid role is required (buyer or seller)' 
      });
    }
    
    const wallet = walletStore[walletId];
    const escrow = escrowStore[escrowId];
    
    // Get wallet address
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    // Verify the user is the specified role
    if (escrow[role] !== userAddress) {
      return res.status(403).json({ 
        status: 'error', 
        message: `Only the ${role} can approve as ${role}` 
      });
    }
    
    // Check if escrow is still active
    if (escrow.fundsReleased) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Funds have already been released' 
      });
    }
    
    // Check if already approved
    if (role === 'buyer' && escrow.buyerApproved) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Buyer has already approved this escrow' 
      });
    }
    
    if (role === 'seller' && escrow.sellerApproved) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Seller has already approved this escrow' 
      });
    }
    
    
    
    const approveTransactionHash = 'approve_' + crypto.randomBytes(32).toString('hex');
    
    // Update escrow status
    if (role === 'buyer') {
      escrowStore[escrowId].buyerApproved = true;
    } else {
      escrowStore[escrowId].sellerApproved = true;
    }
    
    res.json({
      status: 'success',
      escrowId: escrowId,
      transactionHash: approveTransactionHash,
      message: `Escrow approved by ${role}`
    });
    
  } catch (error) {
    console.error('Error approving escrow:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Release escrow funds (when both approved)
app.post('/release-escrow', async (req, res) => {
  try {
    const { walletId, escrowId } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!escrowId || !escrowStore[escrowId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid escrow ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    const escrow = escrowStore[escrowId];
    
    // Get wallet address
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    if (escrow.buyer !== userAddress && escrow.seller !== userAddress) {
      return res.status(403).json({ 
        status: 'error', 
        message: 'Only the buyer or seller can release the funds' 
      });
    }
    
    if (escrow.fundsReleased) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Funds have already been released' 
      });
    }
    
    if (escrow.disputeRaised) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Cannot release funds while dispute is active' 
      });
    }
    
    if (!escrow.buyerApproved || !escrow.sellerApproved) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Both buyer and seller must approve before release' 
      });
    }
    
 
    
    const releaseTransactionHash = 'release_' + crypto.randomBytes(32).toString('hex');
    
    escrowStore[escrowId].fundsReleased = true;
    escrowStore[escrowId].releasedAt = new Date().toISOString();
    
    res.json({
      status: 'success',
      escrowId: escrowId,
      transactionHash: releaseTransactionHash,
      message: 'Funds released successfully'
    });
    
  } catch (error) {
    console.error('Error releasing escrow funds:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Raise a dispute
app.post('/raise-dispute', async (req, res) => {
  try {
    const { walletId, escrowId } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!escrowId || !escrowStore[escrowId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid escrow ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    const escrow = escrowStore[escrowId];
    
    // Get wallet address
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    // Verify user is buyer or seller
    if (escrow.buyer !== userAddress && escrow.seller !== userAddress) {
      return res.status(403).json({ 
        status: 'error', 
        message: 'Only the buyer or seller can raise a dispute' 
      });
    }
    
    // Check if escrow is in a valid state for dispute
    if (escrow.fundsReleased) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Funds have already been released' 
      });
    }
    
    if (escrow.disputeRaised) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Dispute has already been raised' 
      });
    }
    
    // Check if an arbiter exists
    if (!escrow.arbiter) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'This escrow does not have an arbiter to resolve disputes' 
      });
    }
    

    
    // For now, simulate the dispute
    const disputeTransactionHash = 'dispute_' + crypto.randomBytes(32).toString('hex');
    
    // Update escrow status
    escrowStore[escrowId].disputeRaised = true;
    escrowStore[escrowId].disputeRaisedAt = new Date().toISOString();
    escrowStore[escrowId].disputeRaisedBy = userAddress;
    
    res.json({
      status: 'success',
      escrowId: escrowId,
      transactionHash: disputeTransactionHash,
      message: 'Dispute raised successfully'
    });
    
  } catch (error) {
    console.error('Error raising dispute:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Resolve a dispute (arbiter only)
app.post('/resolve-dispute', async (req, res) => {
  try {
    const { walletId, escrowId, deservingParty } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!escrowId || !escrowStore[escrowId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid escrow ID' 
      });
    }
    
    if (!deservingParty || !['buyer', 'seller'].includes(deservingParty)) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Must specify either buyer or seller as the deserving party' 
      });
    }
    
    const wallet = walletStore[walletId];
    const escrow = escrowStore[escrowId];
    
    // Get wallet address
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    // Verify user is the arbiter
    if (escrow.arbiter !== userAddress) {
      return res.status(403).json({ 
        status: 'error', 
        message: 'Only the arbiter can resolve disputes' 
      });
    }
    
    // Check if escrow has an active dispute
    if (!escrow.disputeRaised) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'No dispute has been raised for this escrow' 
      });
    }
    
    if (escrow.fundsReleased) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Funds have already been released' 
      });
    }
    
    // Determine the deserving party's address
    const deservingAddress = escrow[deservingParty];
    
   
    
    // For now, simulate the resolution
    const resolveTransactionHash = 'resolve_' + crypto.randomBytes(32).toString('hex');
    
    // Update escrow status
    escrowStore[escrowId].fundsReleased = true;
    escrowStore[escrowId].releasedAt = new Date().toISOString();
    escrowStore[escrowId].resolvedBy = userAddress;
    escrowStore[escrowId].resolvedInFavorOf = deservingParty;
    
    res.json({
      status: 'success',
      escrowId: escrowId,
      transactionHash: resolveTransactionHash,
      message: `Dispute resolved in favor of the ${deservingParty}`
    });
    
  } catch (error) {
    console.error('Error resolving dispute:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

app.get('/get-pending-escrows', async (req, res) => {
  try {
    const { walletId } = req.query;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });

    

await statePromise;
    
    
    const pendingEscrows = Object.values(escrowStore).filter(
      escrow => (
        escrow.buyer === userAddress && 
        !escrow.fundsReleased && 
        !escrow.buyerApproved
      )
    );
    

    
    res.json({
      status: 'success',
      escrows: pendingEscrows
    });
    
  } catch (error) {
    console.error('Error getting pending escrows:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

// Cancel an escrow 
app.post('/cancel-escrow', async (req, res) => {
  try {
    const { walletId, escrowId } = req.body;
    
    if (!walletId || !walletStore[walletId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid wallet ID' 
      });
    }
    
    if (!escrowId || !escrowStore[escrowId]) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Invalid escrow ID' 
      });
    }
    
    const wallet = walletStore[walletId];
    const escrow = escrowStore[escrowId];
    
    // Get wallet addr
    let userAddress;
    const statePromise = new Promise(resolve => {
      const subscription = wallet.state().subscribe(state => {
        userAddress = state.address;
        subscription.unsubscribe();
        resolve();
      });
    });
    
    await statePromise;
    
    if (escrow.buyer !== userAddress) {
      return res.status(403).json({ 
        status: 'error', 
        message: 'Only the buyer can cancel an escrow' 
      });
    }
    
    if (escrow.fundsReleased) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Funds have already been released' 
      });
    }
    
    if (escrow.disputeRaised) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Cannot cancel while dispute is active' 
      });
    }
    

    const cancelTransactionHash = 'cancel_' + crypto.randomBytes(32).toString('hex');
    
    escrowStore[escrowId].status = 'Cancelled';
    escrowStore[escrowId].cancelledAt = new Date().toISOString();
    
    res.json({
      status: 'success',
      escrowId,
      transactionHash: cancelTransactionHash,
      message: 'Escrow cancelled successfully'
    });
    
  } catch (error) {
    console.error('Error cancelling escrow:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message 
    });
  }
});

//ensures directory exist
const ensureDataDirExists = () => {
    const dataDir = path.join(__dirname, 'data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
      console.log('Created data directory');
    }
  };
  
  ensureDataDirExists();
  
  app.post('/report-address', async (req, res) => {
    try {
      const { address, reason } = req.body;
      
      if (!address) {
        return res.status(400).json({ 
          status: 'error', 
          message: 'Address is required' 
        });
      }
      
   
      
      // Create data directory if it doesn't exist
      ensureDataDirExists();
      
      const reportedFilePath = path.join(__dirname, 'data/reported.txt');
      
      // Load existing reported addresses
      let reportedAddresses = [];
      try {
        if (fs.existsSync(reportedFilePath)) {
          reportedAddresses = fs.readFileSync(reportedFilePath, 'utf8')
            .split('\n')
            .filter(line => line.trim() !== '');
        }
      } catch (readError) {
        console.error('Error reading reported addresses file:', readError);
      }
      
      // Check if address is already reported
      if (reportedAddresses.includes(address)) {
        return res.status(400).json({ 
          status: 'warning', 
          message: 'This address has already been reported' 
        });
      }
      
      // Add the new address to the list
      reportedAddresses.push(address);
      
      // Save the updated list
      try {
        fs.writeFileSync(
          reportedFilePath, 
          reportedAddresses.join('\n'),
          'utf8'
        );
        
        // Optionally log the report with reason to a separate file
        const reportsLogPath = path.join(__dirname, 'data/report_reasons.txt');
        const logEntry = `${new Date().toISOString()} - ${address} - ${reason || 'No reason provided'}\n`;
        
        fs.appendFileSync(reportsLogPath, logEntry, 'utf8');
        
        console.log(`Address reported: ${address}`);
        
        res.json({
          status: 'success',
          message: 'Address reported successfully'
        });
      } catch (writeError) {
        console.error('Error writing to reported addresses file:', writeError);
        throw new Error('Failed to save reported address');
      }
      
    } catch (error) {
      console.error('Error reporting address:', error);
      res.status(500).json({ 
        status: 'error', 
        message: error.message 
      });
    }
  });

// Start the server
startServer();