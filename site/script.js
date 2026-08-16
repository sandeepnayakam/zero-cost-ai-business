// Copy address to clipboard
function copyAddress() {
    const address = document.getElementById('wallet-address').value;
    navigator.clipboard.writeText(address).then(() => {
        alert('Address copied to clipboard!');
    }).catch(err => {
        alert('Copy failed: ' + err);
    });
}