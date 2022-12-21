/* 
 * tcpserver.c - A simple TCP 
 * usage: tcpserver <port>
 */

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <netdb.h>
#include <sys/types.h> 
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>

#define BUFSIZE 16

#if 0
/* 
 * Structs exported from in.h
 */

/* Internet address */
struct in_addr {
    unsigned int s_addr; 
};

struct sr_datafeed_analog {
     //GSList *channels;
     int num_samples;
     int mq;
     int unit;
     uint64_t mqflags;
     float *data;
};

/* Internet style socket address */
struct sockaddr_in  {
    unsigned short int sin_family; /* Address family */
    unsigned short int sin_port;   /* Port number */
    struct in_addr sin_addr;	 /* IP address */
    unsigned char sin_zero[...];   /* Pad to size of 'struct sockaddr' */
};

/*
 * Struct exported from netdb.h
 */

/* Domain name service (DNS) host entry */
struct hostent {
    char    *h_name;        /* official name of host */
    char    **h_aliases;    /* alias list */
    int     h_addrtype;     /* host address type */
    int     h_length;       /* length of address */
    char    **h_addr_list;  /* list of addresses */
}
#endif

/*
 * error - wrapper for perror
 */
void error(char *msg) {
    perror(msg);
    exit(1);
}

int main(int argc, char **argv) {
    int parentfd; /* parent socket */
    int childfd; /* child socket */
    int portno; /* port to listen on */
    int clientlen; /* byte size of client's address */
    struct sockaddr_in serveraddr; /* server's addr */
    struct sockaddr_in clientaddr; /* client addr */
    struct hostent *hostp; /* client host info */
    char buf[BUFSIZE]; /* message buffer */
    char *hostaddrp; /* dotted decimal host addr string */
    int optval; /* flag value for setsockopt */
    int n; /* message byte size */

    /* 
     * check command line arguments 
     */
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        exit(1);
    }
    portno = atoi(argv[1]);

    /* 
     * socket: create the parent socket 
     */
    parentfd = socket(AF_INET, SOCK_STREAM, 0);
    if (parentfd < 0) 
         error("ERROR opening socket");

    /* setsockopt: Handy debugging trick that lets 
     * us rerun the server immediately after we kill it; 
     * otherwise we have to wait about 20 secs. 
     * Eliminates "ERROR on binding: Address already in use" error. 
     */
    optval = 1;
    setsockopt(parentfd, SOL_SOCKET, SO_REUSEADDR, 
        (const void *)&optval , sizeof(int));

    /*
     * build the server's Internet address
     */
    bzero((char *) &serveraddr, sizeof(serveraddr));

    /* this is an Internet address */
    serveraddr.sin_family = AF_INET;

    /* let the system figure out our IP address */
    serveraddr.sin_addr.s_addr = htonl(INADDR_ANY);

    /* this is the port we will listen on */
    serveraddr.sin_port = htons((unsigned short)portno);

    /* 
     * bind: associate the parent socket with a port 
     */
    if (bind(parentfd, (struct sockaddr *) &serveraddr, 
        sizeof(serveraddr)) < 0) 
        error("ERROR on binding");

    /* 
     * listen: make this socket ready to accept connection requests 
     */
    if (listen(parentfd, 5) < 0) /* allow 5 requests to queue up */ 
        error("ERROR on listen");

    /* 
     * main loop: wait for a connection request, echo input line, 
     * then close connection.
     */
    clientlen = sizeof(clientaddr);
    int start_done =0;
    while (1) {

        /* 
         * accept: wait for a connection request 
         */
        childfd = accept(parentfd, (struct sockaddr *) &clientaddr, &clientlen);
        if (childfd < 0) 
            error("ERROR on accept");
    
        /* 
         * gethostbyaddr: determine who sent the message 
         */
        hostp = gethostbyaddr((const char *)&clientaddr.sin_addr.s_addr, 
			  sizeof(clientaddr.sin_addr.s_addr), AF_INET);
        if (hostp == NULL)
            error("ERROR on gethostbyaddr");
        hostaddrp = inet_ntoa(clientaddr.sin_addr);
        if (hostaddrp == NULL)
            error("ERROR on inet_ntoa\n");
        printf("server established connection with %s (%s)\n", 
            hostp->h_name, hostaddrp);

        unsigned char data [16];
        float voltage = 0.0f;
        float current = 0.0f;
        int channel = 1;
        unsigned int logic = 0xAA55AA55U;

        while (1)
        {
            /* 
             * read: read input string from the client
             */
            bzero(buf, BUFSIZE);

            int count;
            ioctl(childfd, FIONREAD, &count);
 
            if (count > 0)
            {
                n  = read(childfd, buf, count);
                printf("%d bytes read\n", n);
            }
            else
            {
                n = 0;
            }
            if (n < 0)
            {	
                error("ERROR reading from socket");
                break;
            }
            if (n != 0)
            { 
                printf("server received %d bytes: %s\n", n, buf);
   
                if (strncmp(buf, "version", 7) == 0)
                {
                    n = write(childfd, "PINA", 4);
                    if (n < 0) 
                        error("ERROR writing to socket");
                    printf("Respond to scan ok\n");
                    close(childfd);
                    break;
                }
                else if (strncmp(buf, "samplerate", 10) == 0)
                {
                    n = write(childfd, "10", 3);
                    if (n < 0)
                        error("ERROR writing to socket");
                    printf("Respond to samplerate ok\n");
                }
                else if (strncmp(buf, "sampleunit", 10) == 0)
                {
                    n = write(childfd, "0", 2);
                    if (n < 0)
                         error("ERROR writing to socket");
                    printf("Respond to sampleunit ok\n");
                }
                else if (strncmp(buf, "sampleunit", 10) == 0)
                {
                    n = write(childfd, "1", 2);
                    if (n < 0)
                        error("ERROR writing to socket");
                    printf("Respond to sampleunit ok\n");
                }
                else if (strncmp(buf, "sampleunit", 10) == 0)
                {
                    n = write(childfd, "1", 2);
                    if (n < 0)
                        error("ERROR writing to socket");
                    printf("Respond to sampleunit ok\n");
                }
                else if (strncmp(buf, "memalloc", 8) == 0)
                {
                    n = write(childfd, "16", 3);
                    if (n < 0)
                        error("ERROR writing to socket");
                    printf("Respond to memalloc ok\n");
                }
                else if ((strncmp(buf, "get", 3) == 0))
                {
                    printf("Respond to get ok %ls\n", (int *)(&data));
                    start_done = 1;
                }
                else if ( (strncmp(buf, "close", 5) == 0))
                {
                    printf("NO Respond to stop ok\n");
                    start_done = 0;
                }
                else if ( (strncmp(buf, "exit", 4) == 0))
                {
	            printf("NO Respond to exit ok\n");
                    start_done = 0;
                    break;
                }
                else
                    printf("Uknown data %d %X %X %X %X\n", n, buf[0], buf[1], buf[2], buf[3]);
            }
            if (start_done)
            {
                current = current + 0.0005f;
                voltage = voltage + 0.0001f;
	        logic = logic + 1;
                memcpy(&data[4], (unsigned char*)&current, 4);
                memcpy(&data[8], (unsigned char*)&voltage, 4);
                memcpy(&data[12], (unsigned char*)&logic, 4);
                write(childfd, &data, sizeof(data));
                printf("send data %f %f %X\n", current, voltage, logic);
            }
            usleep(100000);
        }
        close(childfd);
    }
}