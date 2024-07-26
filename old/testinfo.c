/*
 * Web form which searches database for trwids and/or runids,
 * printing trw_id, runid and data acquisition dates for each
 * test found to match query inputs.
 *
 * Copyright 1998 by the Smithsonian Institute.
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "cgi-lib.h"
#include "html-lib.h"
#include "libpq-fe.h"
#include "mycgi.h"

int debug=0;
PGconn *conn = NULL;

void close_db(void) {
	if (conn != NULL) PQfinish(conn);
}

void begin_html(void) {
	printf("\n\
<HTML>\n\
<HEAD>\n\
<TITLE>XRCF Test Information</TITLE>\n\
</HEAD>\n\
\n\
<BODY>\n\
");
	include("/proj/web-cxc/htdocs/incl/header.html");
	include("/proj/web-cxc/htdocs/incl/cal_h.html");

	printf("\n\
<BR>\n\
\n\
<BLOCKQUOTE>\n\
");

}

void end_html(void) {
	printf("\n\
<HR>\n\
Enter one or more runids and/or TRW_IDs (no special characters, such as\n\
quotes) and for each test see the\n\
<UL>\n\
<LI> <I>TRW_ID</I>\n\
<LI> <I>Runid</I>\n\
<LI> <I>Date</I> (as in /data/hxds/data/...)\n\
</UL>\n\
\n\
<P>\n\
This CGI program was written in C. You can <A HREF=\"http://asc.harvard.edu/cal/Links/Letg/"__FILE__"\">view the\n\
source</A>.\n\
\n\
</BLOCKQUOTE>\n\
<BR><BR>\n\
<I>COMMENTS or ADDITIONS:</I>\n\
<BR>\n\
<A HREF=\"mailto:pratzlaff@cfa.harvard.edu\"><i>Pete Ratzlaff</i></a>\n\
\n\
<BR><BR>\n\
");
	include("/proj/web-cxc/htdocs/incl/footer.html");
	printf("\n\
\n\
</BODY>\n\
</HTML>\n\
");

}

void print_form(char *tests, int regex) {
	printf("\
<FORM METHOD=\"POST\">\n\
\n\
<B>Enter a bunch of TRW_IDs and/or runids</B><BR>\n\
<INPUT TYPE=\"text\" NAME=\"tests\" VALUE=\"%s\" SIZE=80><BR>\n\
<INPUT TYPE=\"checkbox\" NAME=\"regex\" VALUE=\"1\"%s> Enable Regular\n\
Expressions on TRW_IDs<BR>\n\
<INPUT TYPE=\"submit\" NAME=\"Go\" VALUE=\"Go\">\n\
</FORM>\n\
", tests, (regex ? " CHECKED" : "")
	);
}

/*
 * does massaging of form data, setting variables along the way
 */
void process_form_data(char **tests, int *regex) {
	llist data;
	char *regex_char;
	char *debug_char;

	if (read_cgi_input(&data)>0) {
		if (! (*tests = cgi_val(data,"tests"))) *tests = "";
		if (! (regex_char = cgi_val(data,"regex"))) regex_char = "0";
		if (! (debug_char = cgi_val(data,"debug"))) debug_char = "0";
	}
	else {
		*tests = "";
		regex_char = "0";
		debug_char = "0";
	}

	debug = atoi(debug_char);
	*regex = atoi(regex_char);

	if (debug) {
		print_cgi_env();
		print_entries(data);
		printf("tests = '%s'<BR>\n",*tests);
	}
}

char *make_query_string(char *orig_tests, int regex) {
	int size, res = 1024; /* realloc once the query string gets this large */
	char tests[strlen(orig_tests)+1];
	char *token, *op;
	int nparams = 0;
	char *query_string = malloc(res);

	strcpy(tests,orig_tests);
	size = 1024;

	query_string[0] = '\0';
	strcat(query_string,"SELECT trw_id, runid, date FROM trm WHERE");

	if ((token = strtok(tests," ")) == NULL)
		return NULL;
	do {
		int runid = isrunid(token);
		if (!strlen(token)) continue;

		nparams++;

		op = runid || regex ? " = " : " ~ ";

		while (size <
			(
			strlen(query_string) +
			((nparams == 1) ? 0 : strlen("OR ")) +
			(runid ? strlen(" runid") : strlen(" trw_id")) + 2 +
			strlen(op) +
			strlen(token)
			)

		) query_string = realloc (query_string, (size += res));

		if (runid) {
			sprintf(query_string,"%s %srunid%s%s",
				query_string,
				((nparams > 1) ? "OR " : ""),
				op,
				token
			);
		}
		else {
			sprintf(query_string,"%s %strw_id%s'%s'",
				query_string,
				((nparams > 1) ? "OR " : ""),
				op,
				token
			);
		}

	} while ((token = strtok(NULL," ")) != NULL);

	return query_string;
}

void print_query_results(PGresult *result,float query_time) {
	int ntuples = PQntuples(result);
	int i;

	printf("<H2>Query Results</H2>\n");
	printf("%d match%s in %.2f seconds<BR>\n",ntuples,(ntuples == 1) ? "" : "es",query_time);
	if (!ntuples) return;

	printf("\n\
<TABLE border=5 cellpadding=10 cellspacing=5>\n\
<TR align=\"center\">\n\
<TH>TRW_ID</TH> <TH>Runid</TH> <TH>Date</TH> <TH>BND Data Plots</TH>\n\
</TR>\n\
");

	for (i=0; i<ntuples; i++) {
		printf("<TR ALIGN=\"center\">\n<TD>%s</TD><TD>%s</TD><TD>%s</TD><TD><A HREF=\"http://cxc.harvard.edu/cgi-gen/LETG/bnd_view/index.cgi?runid=%s\">Go</A></TD>\n</TR>\n",
			PQgetvalue(result, i,0),
			PQgetvalue(result, i,1),
			PQgetvalue(result, i,2),
			PQgetvalue(result, i,1)
		);
	}
	printf("</TABLE>\n");
}
		
void do_query(char *tests, int regex) {
	char *query_string;
	PGresult *result;
	clock_t start_time;

	if (!(query_string=make_query_string(tests,regex))) return;
	if (debug) printf("query_string = '%s'\n",query_string);

	start_time = clock();
	if (!(conn = PQsetdb(
		"ascda3.cfa.harvard.edu",
		NULL,
		NULL,
		NULL,
		"xrcf"
	))) { free(query_string); return; }
	atexit(close_db);
	if (PQstatus(conn) != CONNECTION_OK) {
		printf(
			"Error Connecting to database:<BR>\n<BLOCKQUOTE>\n%s\n</BLOCKQUOTE>\n",
			PQerrorMessage(conn)
		);
		free(query_string);
		return;
	}

	if (!(result = PQexec(conn, query_string))) {
		printf(
			"Error making database query:<BR>\nquery_string = '<TT>%s</TT>'<BR>\n<BLOCKQUOTE>\n%s\n</BLOCKQUOTE>\n",
			query_string,
			PQerrorMessage(conn)
		);
		free(query_string);
		return;
	}

	free(query_string);
	print_query_results(result,(clock()-start_time)/(float)CLOCKS_PER_SEC);
	PQclear(result);

}

int main(int argc, char **argv) {
	char *tests;
	int regex;
	FILE *err = log_errors(NULL);
	logit(NULL);

	mime_header("text/html");
	begin_html();
	atexit(end_html);

	process_form_data(&tests,&regex);

	do_query(tests,regex);

	print_form(tests,regex);

	if (err) fclose(err);
	return 0;
}
