// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Payment {
    event PaymentSent(address indexed from, address indexed to, uint amount);

    // Function to send payment from the sender to a specified recipient.
    // The function is payable so that it can receive ETH.
    function sendPayment(address _recipient) external payable {
        require(msg.value > 0, "Must send some ETH");
        _recipient.transfer(msg.value);
        emit PaymentSent(msg.sender, _recipient, msg.value);
    }
}
