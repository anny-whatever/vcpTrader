server {
    listen 80;
    server_name api.devstatz.com;

    # Trust Cloudflare IPs
    # You may want to update this list periodically as Cloudflare adds new IP ranges
    real_ip_header CF-Connecting-IP;

    # WebSocket location
    location /socket/ {
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
        proxy_pass http://127.0.0.1:8000/socket/;
        expires off;
        add_header Pragma no-cache;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always;
    }

    # Standard API and other routes
    location / {
        proxy_buffering off;
        # Pass Cloudflare specific headers
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
        proxy_set_header CF-IPCountry $http_cf_ipcountry;
        proxy_set_header CF-Ray $http_cf_ray;
        proxy_set_header CF-Visitor $http_cf_visitor;

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;

        # Direct proxy to backend without redirection
        proxy_pass http://127.0.0.1:8000;

        # Disable redirects to veloria.in
        proxy_redirect off;

        # Cache control
        expires off;
        add_header Pragma no-cache;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always;
    }
}
