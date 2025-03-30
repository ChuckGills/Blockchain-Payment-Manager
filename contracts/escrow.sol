// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Escrow {
    address public buyer;
    address public seller;
    address public arbiter;
    uint public amount;
    bool public buyerApproved;
    bool public sellerApproved;
    bool public fundsReleased;
    bool public disputeRaised;

   
    constructor(address _seller, address _arbiter) payable {
        require(msg.value > 0, "Must deposit funds");
        buyer = msg.sender;
        seller = _seller;
        arbiter = _arbiter;
        amount = msg.value;
    }


    function approveByBuyer() external {
        require(msg.sender == buyer, "Only buyer can approve");
        require(!fundsReleased, "Funds already released");
        buyerApproved = true;
    }

    
    function approveBySeller() external {
        require(msg.sender == seller, "Only seller can approve");
        require(!fundsReleased, "Funds already released");
        sellerApproved = true;
    }

    
    function dispute() external {
        require(msg.sender == buyer || msg.sender == seller, "Only buyer or seller can dispute");
        require(!fundsReleased, "Funds already released");
        disputeRaised = true;
    }

    
    function releaseFunds() external {
        require(buyerApproved && sellerApproved, "Both parties must approve");
        require(!fundsReleased, "Funds already released");
        require(!disputeRaised, "Dispute raised, cannot auto-release");
        fundsReleased = true;
        payable(buyer).transfer(amount);
    }

    
    function resolveDispute(address payable deservingParty) external {
        require(msg.sender == arbiter, "Only arbiter can resolve dispute");
        require(disputeRaised, "No dispute raised");
        require(!fundsReleased, "Funds already released");
        require(deservingParty == buyer || deservingParty == seller, "Deserving party must be buyer or seller");

        fundsReleased = true;
        uint arbiterFee = (amount * 1) / 100; // 1% fee
        uint payout = amount - arbiterFee;    // 99% payout
        payable(arbiter).transfer(arbiterFee);
        payable(deservingParty).transfer(payout);
    }
}