// Description: Client for UNIX domain socket
// Compiled: gcc ssock.c -o ssock
// made by: cylian914
#include <stdio.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <string.h>
#include <unistd.h>

int message(int *sock, char *mess, char *reply){
  write(*sock, mess, strlen(mess)+1);
  read(*sock,reply,1024);
  printf("Message: %s\n", mess);
  printf("Received: %s\n", reply);
  return 0;
}
int main(int argc, char *argv[]) {
  if (argc < 2) {
    printf("Usage: %s <path> <message>\n", argv[0]);	
    printf("If message is ommited stdin we be used\n");
    printf("Example:\n\t%s /tmp/mysocket hello\n", argv[0]);
    printf("\techo \"hello\" | %s /tmp/mysocket\n", argv[0]);
    printf("\tBoth examples will send \"hello\" to server\n");
    printf("Multiple message can be send with one connection using stdin\n");
    return 1;
  }


  int sock = socket(AF_UNIX, SOCK_STREAM, 0);
  struct sockaddr_un serverAddress = {0};
  serverAddress.sun_family  = AF_UNIX; 
  strcpy(serverAddress.sun_path, argv[1]);
  
  printf("Connecting to %s\n", argv[1]);
  int resv;
  resv=connect(sock, (struct sockaddr*)&serverAddress, SUN_LEN(&serverAddress));
  if (resv < 0)
    return resv;
  printf("Connected\n");
 
  char mess[1024];
  char reply[1024];
  size_t n = 0;
  if (argc == 2) {
    while (fgets(mess, 1024, stdin)!=NULL){
      message(&sock, mess, reply);
    }
  }
  else
  {
    //  concat argv
    memcpy(mess,argv[2],strlen(argv[2])+1);
    for(int i=3; i<argc; i++){
      strcat(mess," ");
      strcat(mess,argv[i]);
    }
    message(&sock, mess, reply);
  }
  close(sock);
  return 0;
}


