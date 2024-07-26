.SUFFIXES: .c .o .cgi

include /home/rpete/www/c/Makefile.common

CC = gcc
CFLAGS = -Wall -O2

.c.o:
	$(CC) $(CFLAGS) -c $< -o $*.o $(MYCGI_INCLUDE) $(CGIHTML_INCLUDE) $(PG_INCLUDE)

.o.cgi:
	$(CC) $< -o $@ -lsocket $(MYCGI_LIB) $(CGIHTML_LIB) $(PG_LIB)
	strip $@
