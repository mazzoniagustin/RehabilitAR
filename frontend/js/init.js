(async function init() {
    if (getToken()) {
        await loadDashboard();
    }
})();

// Atajo de teclado para login
document.getElementById('loginPassword')?.addEventListener('keydown', e => { 
    if(e.key === 'Enter') handleLogin(); 
});