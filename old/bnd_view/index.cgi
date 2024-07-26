#!/usr/bin/perl
use strict;

sub begin_html {
	print <<EOP;
<HTML>

<HEAD>

<META NAME="author" CONTENT="Pete Ratzlaff">
<TITLE>BND Data Viewer</TITLE>

</HEAD>

<BODY BGCOLOR="white">
EOP
	return 1;
}

sub end_html {
	print <<EOP;
<HR>
To complain, contact Pete Ratzlaff:
<ADDRESS><A HREF="mailto:pratzlaff\@cfa.harvard.edu">pratzlaff\@cfa.harvard.edu</A></ADDRESS>

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
	open(ERROR_LOG, '>>/dev/null');
	carpout(\*ERROR_LOG);
}
END {
	end_html();
}

use Config;
use lib '/home/rpete/local/perlmods';
use lib '/home/rpete/local/perlmods/'.$Config{archname};

use MyCGI_Lite;
my $q=new MyCGI_Lite;
#$q->logit;

my %FORM=$q->parse_form_data;

my $error_msg='';

# parameters describing our 'window' into the data
my %DEFAULTS = (
	'ssd_xlo' => 0,
	'ssd_xhi' => 4095,
	'ssd_rlo' => 0,
	'ssd_rhi' => 4095,
	'fpc_xlo' => 0,
	'fpc_xhi' => 511,
	'fpc_rlo' => 0,
	'fpc_rhi' => 511,
);
my %FINAL=(); # parameters sent to 'mkplots.cgi'

#
# every input field should be numeric, except for 'iterations'
#
foreach (keys %FORM) {
	next if ($_ eq 'iterations');
	defined $FORM{$_} or do { delete $FORM{$_}; next };
	$FORM{$_} =~ s/^\s+(.*?)\s+/$1/;
	$FORM{$_} =~ /^\d+$/ or do { delete $FORM{$_}; next };
}

#
# check validity of runid input
#
exists $FORM{runid} or $FORM{runid} = '';
length $FORM{runid} and ($FORM{runid} !~ /^1\d{5}$/) and
	on_error("Invalid runid input: '$FORM{runid}'");

# make comma-separated list of requested iterations
exists $FORM{iterations} or $FORM{iterations}='';
my @I=();
foreach (split /\s+/, $FORM{iterations}) {
	if (/^\d+$/) { push @I, int }
	elsif (/^(\d+)\.\.(\d+)$/) {
		push @I, ($1 <= $2) ? ($1..$2) : ($2..$1)
	} elsif (/^(\d+)-(\d+)$/) {
		push @I, ($1 <= $2) ? ($1..$2) : ($2..$1)
	} else {
		on_error("Invalid iteration input: '$FORM{iterations}'");
	}
}
my $itstr=join(',',@I);

# now, we'll set up %FINAL (this is passed to mkplot.cgi)
foreach (keys %DEFAULTS) {
	$FINAL{$_} = (length $FORM{$_}) ? $FORM{$_} : $DEFAULTS{$_};
}

# finally, go through the pairs
# if 
# 1. either is out of range
# 2. the lesser is ge the greater
# then set both to default
foreach (['ssd_xlo','ssd_xhi'],['fpc_xlo','fpc_xhi']) {
	my ($l,$h)=@{$_};
	if (
		$FINAL{$l} < $DEFAULTS{$l} or
		$FINAL{$l} > $DEFAULTS{$h} or
		$FINAL{$h} > $DEFAULTS{$h} or
		$FINAL{$h} < $DEFAULTS{$l} or
		$FINAL{$l} >= $FINAL{$h}
	) { ($FINAL{$l},$FINAL{$h}) = ($DEFAULTS{$l},$DEFAULTS{$h}) }
}

if (! length $error_msg and length $FORM{runid}) {
	my $query_string='';
	foreach (keys %DEFAULTS) { $query_string .= $_.'='.$FINAL{$_}.'&' }
	$query_string .= "runid=".$FORM{runid};
	$query_string .= "&iterations=$itstr";
	print "<IMG SRC=\"./mkplots.cgi?".$query_string."\" ALT=\"Plots of each BND for this runid\">";
}
else { print "<HR>\n" }
mkform();
print "\n<P>\n${\($q->cfa_logo_link)}\n";
exit;

sub mkform {
	print <<EOP;
<FORM METHOD="POST">
<TABLE>
<TR ALIGN="left">
<TD><A HREF="bnd_view_help.cgi?runid=">Runid</A></TD>
<TD><INPUT TYPE="text" NAME="runid" VALUE="$FORM{runid}" SIZE=6 MAXLENGTH=6> <I>(required)</I></TD>
</TR>
<TR ALIGN="left">
<TD><A HREF="bnd_view_help.cgi?iterations=">Iterations</A></TD>
<TD><INPUT TYPE="text" NAME="iterations" VALUE="$FORM{iterations}" SIZE=20></TD>
</TABLE>

<TABLE>
<TR ALIGN=center> <TH></TH> <TH COLSPAN=2>FPC Parameters</TH> <TH COLSPAN=2>SSD Parameters</TH> </TR>
<TR ALIGN=left>
<TD><A HREF="bnd_view_help.cgi?plot_range=">Plot Range</A></TD>
<TD><I>min</I> <INPUT TYPE=text NAME="fpc_xlo" VALUE="$FORM{fpc_xlo}" SIZE=3 MAXLENGTH=3></TD>
<TD><I>max</I> <INPUT TYPE=text NAME="fpc_xhi" VALUE="$FORM{fpc_xhi}" SIZE=3 MAXLENGTH=3></TD>
<TD><I>min</I> <INPUT TYPE=text NAME="ssd_xlo" VALUE="$FORM{ssd_xlo}" SIZE=4 MAXLENGTH=4></TD>
<TD><I>max</I> <INPUT TYPE=text NAME="ssd_xhi" VALUE="$FORM{ssd_xhi}" SIZE=4 MAXLENGTH=4></TD>
</TR>

<TR ALIGN=left>
<TD><A HREF="bnd_view_help.cgi?roi=">ROI</A></TD>
<TD><I>min</I> <INPUT TYPE=text NAME="fpc_rlo" VALUE="$FORM{fpc_rlo}" SIZE=3 MAXLENGTH=3></TD>
<TD><I>max</I> <INPUT TYPE=text NAME="fpc_rhi" VALUE="$FORM{fpc_rhi}" SIZE=3 MAXLENGTH=3></TD>
<TD><I>min</I> <INPUT TYPE=text NAME="ssd_rlo" VALUE="$FORM{ssd_rlo}" SIZE=4 MAXLENGTH=4></TD>
<TD><I>max</I> <INPUT TYPE=text NAME="ssd_rhi" VALUE="$FORM{ssd_rhi}" SIZE=4 MAXLENGTH=4></TD>
</TR>
</TABLE>
<P>
<INPUT TYPE="submit" NAME="Go" VALUE="Go"</FORM>
EOP
	return 1;
}

# an error was found
sub on_error {
	$error_msg=shift;
	print <<EOP;
An error has occurred. The following message was given as the reason...<P>
<BLOCKQUOTE><PRE>
$error_msg
</PRE></BLOCKQUOTE>
<P>
EOP
}
