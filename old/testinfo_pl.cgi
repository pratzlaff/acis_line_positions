#!/opt/local/bin/perl
use strict;

#
# This program was written by Pete Ratzlaff, and is Copyright 1998 by
# the Smithsonian Institute.
#

sub begin_html {
	print <<EOP;
<HTML>

<HEAD>
<TITLE>XRCF Test Information</TITLE>
</HEAD>

<BODY>
EOP

 return 1;
}

sub end_html {
	print <<EOP;
<HR>
This CGI program was written in <A HREF="http://www.perl.com">Perl</A>.
You may <A HREF="testinfo_pl.cgi?source">view
the source</A>.
For more information, contact Pete Razlaff
<ADDRESS>
<A HREF="mailto:pratzlaff\@cfa.harvard.edu">pratzlaff\@cfa.harvard.edu</A>
</ADDRESS>

</BODY>
</HTML>
EOP

	return 1;
}

BEGIN {
	print "Content-type: text/html\n\n";
	begin_html();
	use CGI::Carp qw( carpout fatalsToBrowser );
#	open(ERROR_LOG, ">>/home/rpete/www/base/error_log") or
#		die("error log problem: $!\n");
	open(ERROR_LOG, '>> /dev/null');
	carpout(\*ERROR_LOG);
}

END {
	end_html();
}

use Config;
use lib '/home/rpete/local/perlmods';
use lib '/home/rpete/local/perlmods/'.$Config{archname};
use MyCGI_Lite;
use Pg;
my %FORM;
my @tests=();

DO_LOOKUP: {

	#
	# query results
	#
	my $q=new MyCGI_Lite;
#	$q->logit;
	%FORM=$q->parse_form_data;
	exists $FORM{source} and print_source();
	defined $FORM{tests} or last DO_LOOKUP;

	#
	# list of tests to try
	#
	my @tmp=split /\s+/, $FORM{tests};
	@tests=();
	foreach (@tmp) { push @tests, $_ if length }
	@tests or last DO_LOOKUP;

	print "<H2>Query Results</H2>\n";

	#
	# make db connection
	#
	my $conn=Pg::connectdb("host=ascda3.cfa.harvard.edu dbname=xrcf");
	db_cmp_eq($conn->status,PGRES_CONNECTION_OK,$conn);

	my @bad_runids = my @bad_trwids = ();

	my $table=0;
	foreach (@tests) {

		#
		# do query
		#
		my $s= 'SELECT trw_id, runid, date FROM trm WHERE ';
		if (/^1\d{5}$/) { $s .= "runid = $_;" }
		elsif (defined $FORM{regex} and $FORM{regex}) { $s .= "trw_id ~ '$_';" }
		else { $s .= "trw_id = '$_';" }
		my $result = $conn->exec($s);

		#
		# begin query output table if necessary
		#
		if ($result->ntuples and ! $table) {
			query_table_begin();
			$table = 1;
		}

		#
		# query output
		#
		if ($result->ntuples) {
			for (my $i=0; $i < $result->ntuples; $i++) {
				query_table_entry(
					$result->getvalue($i,0),
					$result->getvalue($i,1),
					$result->getvalue($i,2),
				);
			}
		}
		else {
			if (/^1\d{5}$/) { push @bad_runids, $_ }
			else { push @bad_trwids, $_ }
		}
			
	}
	$table and query_table_end();

	@bad_trwids and do {
		print <<EOP;
Empty queries resulted for the following input <I>TRW_IDs</I>:<BR>
<UL>
EOP
		foreach (@bad_trwids) { print "<LI><PRE>$_</PRE>\n" }
		print "</UL>\n<P>\n";
	};

	@bad_runids and do {
		print <<EOP;
Empty queries resulted for the following input <I>runids</I>:<BR>
<UL>
EOP
		foreach (@bad_runids) { print "<LI><PRE>$_\n</PRE>" }
		print "</UL>\n<P>\n";
	};
	print "<HR>\n";
}

print <<EOP;
<FORM METHOD="POST" ENCTYPE="application/x-www-form-urlencoded">

<STRONG>Enter a bunch of TRW_IDs and runids</STRONG><BR>
<INPUT TYPE="text" NAME="tests" VALUE="${\(join(' ',@tests))}" SIZE=80><BR>
<INPUT TYPE="checkbox" NAME="regex" VALUE="1" ${\( defined $FORM{regex} and $FORM{regex} and ' CHECKED')}> Enable Regular Expressions on TRW_IDs<BR>
<INPUT TYPE="submit" NAME="Go" VALUE="Go">
<HR>
Enter one or more runids or TRW_IDs (no special characters, such as quotes)
and for each test see the
<UL>
<LI> <I>TRW_ID</I>
<LI> <I>Runid</I>
<LI> <I>Date</I> (as in /data/hxds/data/...)
</UL>
EOP
exit;

sub query_table_begin {
	print <<EOP;
<TABLE border=5 cellpadding=10 cellspacing=5>
<TR align="center">
<TH>TRW_ID</TH> <TH>Runid</TH> <TH>Date</TH> <TH>BND Data Plots</TH>
</TR>
EOP
	return 1;
}

sub query_table_entry {
	my ($T,$R,$D) = @_;
	print <<EOP;
<TR ALIGN="center">
<TD>$T</TD> <TD>$R</TD> <TD>$D</TD> <TD><A href="http://cxc.harvard.edu/cgi-gen/LETG/bnd_view/index.cgi?runid=$R">Go</A></TD>
</TR>
EOP
	return 1;
}

sub query_table_end {
	print <<EOP;
</TABLE>
<P>
EOP
	return 1;
}

sub db_cmp_eq($$) {
	my ($cmp,$ret,$conn)=(shift,shift,shift);
	die 'database error: '.$conn->errorMessage."\n" unless ($cmp eq $ret);
}

sub print_source {
	local $_;
	open(FH,$0) or die;
	print "<PRE>\n";
	while (<FH>) {
		s/</&lt;/g;
		s/>/&gt;/g;
		print;
	}
	print "</PRE>\n";
	exit 0;
}
