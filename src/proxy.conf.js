const PROXY_CONFIG = [
    {
        context: [
            "/api",
            "/socket.io",
            "/jira-proxy"
        ],
        target: "http://backend:5000",
        secure: false,
	changeOrigin: true
    }
]

module.exports = PROXY_CONFIG;
