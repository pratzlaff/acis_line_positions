#! /usr/bin/perl
use strict;

use CGI;
use URI::Escape;

my $q = new CGI;

print $q->header;

print $q->start_html(-title => 'ACIS-S / Grating Spectral Feature Positions',
		     -style=>{'src'=>'/incl/cxcstyle_hfonly.css'},
		     );

include('/proj/web-cxc/htdocs/incl/cxcheader.html');

print $q->h1('ACIS-S / Grating Spectral Feature Positions');

my $plotit;

my $features_string = ''; # sent to plotting program

if ($q->param('Go')) {
    my ($names, $wav);
    if (check_data($q) and
	($names, $wav) = get_features($q)
	) {
	$plotit = 1;
	$features_string = join ';', map "$names->[$_] $wav->[$_]", 0..$#{$names};
    }
}

print $q->start_form( -action => './alp.cgi' );


print '<table><tr><td>';

print $q->i('Grating: '), $q->radio_group(
		      -name => 'grating',
		      -values=>['LETG', 'MEG', 'HEG'],
		      -default => 'LETG',
		      ), $q->p;

=begin comment

print $q->i('Subarray: '), $q->radio_group(
				    -name => 'subarray',
				    -values=>['1', '1/2', '1/4', '1/8'],
				    -default => '1',
				    ), $q->p;

=cut

print $q->i('Yoffset (arcmin): '), $q->textfield(
					  -name => 'yoffset',
					  -default => 0,
					  -size => 10,
					  ), $q->p;

=begin comment

print $q->i('SIM-Z offset (arcmin): '), $q->textfield(
		    -name => 'zoffset',
		    -default => 0,
		    -size => 10,
		    ), $q->p;

=cut

print $q->i('Redshift z: '), $q->textfield(
		    -name => 'z',
		    -default => 0,
		    -size => 10,
		    ), $q->p;
		    
print $q->i('Dither full-amplitude (arcsec): '), $q->textfield(
		    -name => 'dither',
		    -default => 32,
		    -size => 10,
		    ), $q->p;

print $q->i('Aimpoint CHIPX: '), $q->textfield(
		    -name => 'chipxaim',
		    -default => 193.74,
		    -size => 10,
		    ), $q->p;

my $default_features = <<'EOP';
C-Ly\ga    33.73
C-He\ga(r) 40.27
C-He\ga(f) 41.47

N-Ly\ga    24.78
N-He\ga(r) 28.79
N-He\ga(f) 29.53

O-Ly\ga    18.97
O-He\ga(r) 21.60
O-He\ga(f) 22.10

Ne-Ly\ga    12.134
Ne-He\ga(r) 13.447
Ne-He\ga(f) 13.699

Mg-Ly\ga     8.421
Mg-He\ga(r)  9.169
Mg-He\ga(f)  9.314

Si-Ly\ga     6.182
Si-He\ga(r)  6.648
Si-He\ga(f)  6.740

S-Ly\ga     4.729
S-He\ga(r)  5.039
S-He\ga(f)  5.102

Ar-Ly\ga     3.733
Ar-He\ga(r)  3.949
Ar-He\ga(f)  3.994

Ca-Ly\ga     3.020
Ca-He\ga(r)  3.177
Ca-He\ga(f)  3.211

Fe-Ly\ga     1.780
Fe-He\ga(r)  1.850
Fe-He\ga(f)  1.868


EOP

print $q->i('Features: '), $q->textarea( -name => 'features',
		    -default => $default_features,
		    -rows => 15,
		    -columns => 30,
		    ), $q->br;
		    
print $q->submit( -name => 'Go' ), $q->defaults;
print '</td><td>';

print <<EOP;
<h3>How to use</h3>

Features may be deleted from or added to the default list; added
features will appear in black. Feature names use PGPLOT text escape
sequences (\\u, \\g, etc.). After submission, a PDF file may
also be downloaded for printing or higher-resolution examination.

<h3>Changes for Cycle 24 (Fall 2022)</h3>
For Cycle 24, ACIS/grating observations use an aimpoint of
ACIS-S3 CHIPX=193.74 instead of 210, and dither is increased
to 32" full width (from 16") in the dispersion direction.  This page
uses those new settings as defaults.

<h3>Caveats</h3>
Note that
because of the difficulty of maintaining precise temperatures in the
telescope structure, errors in source location on the detector may
reach &plusmn;15" in Y, although excursions beyond 10" are very rare (see <a
href="http://cxc.cfa.harvard.edu/mta/ASPECT/aimpoint_mon/index_static.html">"Intra-observation
aimpoint drift" DY plot</a>).
These aim point errors do
<i>not</i> affect absolute astrometry, which is good to much better than 1".
<p>
Near chip edges, dither may cause some of the line flux to be lost;
lines that fall outside the dithered edges (marked in dark gray) will
not be affected.
The standard dither of 32" (peak to peak) corresponds to
1.8 &Aring; for the LETG, 0.72 &Aring; for MEG, and 0.36 &Aring; for HEG.
If important features are expected near chip gaps (e.g., 0th order
near the S2/S3 gap), users must
allow an adequate margin for aim point errors.

<!--
Future enhancements of this tool may include illustrations of
subarrays and where the spectrum falls in Z (vertically).
-->

EOP

print '</td></tr></table>';
print $q->end_form;

plotit($q, $features_string) if $plotit;

print '<p>Questions or comments? Contact <a href="mailto:pratzlaff@cfa.harvard.edu">Pete Ratzlaff</a>.';

include('/proj/web-cxc-dmz/htdocs/incl/cxcfooter.html');

print $q->end_html;

sub include {
  my $file = shift;
  open FH, '< '.$file or die;
  print while <FH>;
  close FH;
}

sub plotit {
    my ($q, $features_string) = @_;

    my $query_string =
	join '&',
#	'subarray='.uri_escape($q->param('subarray')),
	'yoffset='.uri_escape($q->param('yoffset')),
#	'zoffset='.uri_escape($q->param('zoffset')),
	'z='.uri_escape($q->param('z')),
	'dither='.uri_escape($q->param('dither')),
	'chipxaim='.uri_escape($q->param('chipxaim')),
	'grating='.uri_escape($q->param('grating')),
	'features='.uri_escape($features_string),
	;

    my $ps_query_string = $query_string;

    $query_string .= '&swapbg=1&dev='.uri_escape('-/png');
    $ps_query_string .= '&dev='.uri_escape('-/pdf');
    my $url = '/cgi-gen/LETG/alp-plot.cgi?' . $query_string;

    my $ps_url = '/cgi-gen/LETG/alp-plot.cgi?' . $ps_query_string;

    print '<p><a href="'.$ps_url.'">Download PDF</a><br>';
    print $q->img( { alt => "ACIS-S diagram", src => $url } );
}


sub check_data {
    my $q = shift;
    my $retval = 1;

    my $float_re = qr/^([+-]?)(?=\d|\.\d)\d*(\.\d*)?([Ee]([+-]?\d+))?$/;

=begin comment

    if ($q->param('subarray') !~ m!^1|1/2|1/4|1/8$!) {
	print_error($q, "invalid subarray = '".$q->param('subarray'));
	$retval = 0;
    }

=cut

    if ($q->param('grating') !~ /^LETG|MEG|HEG$/) {
	print_error($q, "invalid grating = '".$q->param('grating'));
	$retval = 0;
    }

    if ($q->param('yoffset') !~ $float_re) {
	print_error($q, "invalid SIM-Y offset = '".$q->param('yoffset'));
	$retval = 0;
    }

=begin comment

    if ($q->param('zoffset') !~ $float_re) {
	print_error($q, "invalid SIM-Z offset = '".$q->param('zoffset'));
	$retval = 0;
    }

=cut

    if ($q->param('z') !~ $float_re) {
	print_error($q, "invalid redshift z = '".$q->param('z'));
	$retval = 0;
    }

    if ($q->param('dither') !~ $float_re) {
	print_error($q, "invalid dither = '".$q->param('dither'));
	$retval = 0;
    }

    return $retval;

}

sub print_error {
    my ($q, @errs) = @_;
    for (@errs) {
	print $q->font( { -color => 'red' },
		       '<b>Error:</b> '.$q->escapeHTML($_). "<br>\n"
		       );
    }
}

sub get_features {
    my $q = shift;

    my (@name, @wav);

    # newline is delimiter
    my @features = split "\n", $q->param('features');

    # strip semicolons, leading/trailing whitespace
    tr/;//d, s/^\s+//g, s/\s+$//g for @features;

    @features = grep { length } @features;

    for (@features) {
	my ($name, $wav);
	if (!/^(?:(.*?)\s+)?(-?\d+\.?\d*)$/) {
	    print_error($q, "invalid spectral feature = '$_'");
	    return
	}
	else {
	    push @name, $1;
	    push @wav, $2;
	}
    }

    return \(@name, @wav);
}
