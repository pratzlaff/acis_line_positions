#!/usr/bin/perl

sub begin_html {
	print <<EOP;
<html>
<head>
<title>Help for BND_VIEW</title>
</head>
<body>
EOP
	return 1;
}

sub end_html {
	print <<EOP;
</body>
</html>
EOP
	return 1;
}

BEGIN {
	print "Content-type: text/html\n\n";
	begin_html();
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

my %HELP=(
	'runid' => sub {
print <<EOP;
<h2>Runid for BND_VIEW</h2>
This should be a valid six-digit runid with no special characters, such
as quotes. An invalid runid results in an error.
<p>
Example:
<pre>
115933
<pre>
EOP
},
	'iterations' => sub {
print <<EOP;
<h2>Iterations for BND_VIEW</h2>
Input should be space-separated list of valid iteration numbers for
the given runid. Single values and ranges are allowed.
<p>
Example (we want iterations 0 through 10):
<pre>
0..10
0-10
0 1 2 3 4 5 6 7 8 9 10
</pre>
<p>
Example (we want iterations 0, 2, 4, 5 and 6):
<pre>
0 2 4 5 6
0 2 4-6
0 2 4..6
<pre>
<p>
Example (we want iterations 0-10, with iterations 2 and 5 weighted three times more heavily than the others):
<pre>
0 1 2 2 2 3 4 5 5 5 6 7 8 9 10
0-10 2 2 5 5
0..10 2 2 5 5
</pre>
<p>
<strong><i>Defaults to all iterations in case of no input</i></strong>
EOP
},
	'plot_range' => sub {
print <<EOP;
<h2>Plot Range for BND_VIEW</h2>
The channels spanning the X range of the plot. For FPC, should be
between 0 and 511, for SSD, should be between 0 and 4095. This affects
only the look of the plots.
EOP
},
	'roi' => sub {
print <<EOP;
<h2>ROI for BND_VIEW</h2>
The Region Of Interest (ROI) is that region for which a sum is done and
printed beneath the axis of each plot. For FPC, should be between
0 and 511, for SSD, should be between 0 and 4095.
EOP
},
);

my $helped=0;

KEYS: foreach (keys %HELP) {
	if (defined $FORM{$_}) {
		&{$HELP{$_}};
		$helped=1;
		last KEYS;
	}
}

unless ($helped) {
	foreach (keys %HELP) {
		print "<hr>\n";
		&{$HELP{$_}};
	}
}
