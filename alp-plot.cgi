#! /bin/sh

PERL5LIB=./build/perlmods
export PERL5LIB

LD_LIBRARY_PATH=./lib:./build/pgplot-5.22
export LD_LIBRARY_PATH

PGPLOT_DIR=./build/pgplot-5.22
export PGPLOT_DIR

exec /usr/bin/perl -x -S $0 ${1+"$@"} # -*-perl-*-

#! /usr/bin/perl
use strict;

#BEGIN {
#print $ENV{LD_LIBRARY_PATH},"\n";
#print $ENV{PERL5LIB},"\n";
#print $ENV{PGPLOT_DIR},"\n";
#};

use CGI::Carp qw(fatalsToBrowser);

=head1 NAME

alp - show spectral line positions on ACIS-S

=head1 SYNOPSIS

alp [options]

=head1 DESCRIPTION

Displays ACIS-S cartoon with indications of positions of prominent spectral
lines. Can be useful for determing where lines of interest will be relative
to chip gaps and edges. The default configuration is with LETG and the
recommended SIM-Y offset of 0. These can be changed with options
I<--grating> and I<--yoffset>. Standard spectral lines shown are:

C<
H-like O	Ly-alpha	18.97 Ang
H-like C	Ly-alpha	33.73
H-like N	Ly-alpha	24.78
He-like C	K-alpha(r)	40.27
He-like C	K-alpha(f)	41.47
He-like N	K-alpha(r)	28.79
He-like N	K-alpha(f)	29.53
He-like O	K-alpha(r)	21.60
He-like O	K-alpha(f)	22.10
>

The lines displayed can be custom-configured with the I<--linelist> option.
Wavelength positions on the chips are interpolated linearly from observed
wavelengths at each chip edge for the LETG. When MEG or HEG positions are
requested, the observed LETG wavelength positions are adjusted according to
the ratio of grating facet periods between LETG/MEG or LETG/HEG, as well
as the adjustment for grating clocking angles.

=head1 OPTIONS

=over 4

=item --help

Show help and exit.

=item --version

Show version and exit.

=item --dev=s

PGPLOT device to use (default is /xs). For example, to create a color
Postscript file, C<--dev=filename.ps/cps>

=item --grating=s

Default is C<LETG>. Valid options also include C<MEG> and C<HEG>.

=item --yoffset=f

SIM-Y offset, in arcmin. Default value is zero.

=item --zoffset=f

SIM-Z offset, in arcmin. Default value is zero.

=item --z=f

Redshift I<z>.

  lambda observed = lambda rest * (1 + z)

Default value is zero.

=item --dither=f

Full-amplitude of the dither pattern, in arcsec. The dither region is
displayed on the chip edges as a solid red area. The default value is 16".

=back

=head1 AUTHOR

Pete Ratzlaff E<lt>pratzlaff@cfa.harvard.eduE<gt> December 2004

=head1 SEE ALSO

perl(1).

=cut

#BEGIN {
  #$ENV{PGPLOT_DIR} = './pgplot-5.22';
#};

my $version = '0.1';

use FindBin;

#use lib './perlmods/';

use PGPLOT;
use Math::Trig qw( pi );
use CGI;

# FIXME
$CGI::Application::LIST_CONTEXT_WARN = 0;

use Carp;

# Rowland diameters, mm
use constant LETG_D => 8637.0;
use constant MEG_D => 8633.69;
use constant HEG_D => 8633.69;

# grating periods, AA
use constant LETG_P => 9912.16;
use constant MEG_P => 4001.41;
use constant HEG_P => 2000.81;

# dispersion angles, degrees
use constant LETG_A => 0;
use constant MEG_A => 4.725;
use constant HEG_A => -5.235;

use constant KEV_ANG => 12.398541;

use constant ACIS_UM_PIX => 23.985; # ACIS-S pixel size in microns
use constant ACIS_ARCSEC_PIX => 0.492; # ACIS-S pixel size in arcsec

use Getopt::Long;

my %default_features = (
			'C-Ly\ga', 33.73,
			'C-He\ga(r)', 40.27,
			'C-He\ga(f)', 41.47,
			'N-Ly\ga', 24.78,
			'N-He\ga(r)', 28.79,
			'N-He\ga(f)', 29.53,
			'O-Ly\ga', 18.97,
			'O-He\ga(r)', 21.60,
			'O-He\ga(f)', 22.10,
			'Ne-Ly\ga', 12.134,
			'Ne-He\ga(r)', 13.447,
			'Ne-He\ga(f)', 13.699,
			'Mg-Ly\ga', 8.421,
			'Mg-He\ga(r)', 9.169,
			'Mg-He\ga(f)', 9.314,
			'Si-Ly\ga', 6.182,
			'Si-He\ga(r)', 6.648,
			'Si-He\ga(f)', 6.740,
			'S-Ly\ga', 4.729,
			'S-He\ga(r)', 5.039,
			'S-He\ga(f)', 5.102,
			'Ar-Ly\ga', 3.733,
			'Ar-He\ga(r)', 3.949,
			'Ar-He\ga(f)', 3.994,
			'Ca-Ly\ga', 3.020,
			'Ca-He\ga(r)', 3.177,
			'Ca-He\ga(f)', 3.211,
			'Fe-Ly\ga', 1.780,
			'Fe-He\ga(r)', 1.850,
			'Fe-He\ga(f)', 1.868,
		       );

my %default_opts = (
		    dev => '/xs',
		    yoffset => 0, # SIM-Y offset, arcmin
		    zoffset => 0, # SIM-Z offset, arcmin
# default aimpoint assumed at (chipx, chipy) = (206, 501), changes in
# the aimpoint positions are accomadated here
		    chipxaim =>  193.74,
		    chipyaim =>  491,
		    dither => 32, # dither full amplitute, arcsec
		    grating => 'LETG',
		    z => 0,
		    subarray => '1',
		    );
my %opts = %default_opts;
GetOptions(\%opts,
	   'help!', 'version!', 'dev=s', 'yoffset=f', 'zoffset=f',
	   'dither=f', 'grating=s', 'z=f', 'cgi!', 'swapbg!',
	   'features=s', 'subarray=s', 'chipxaim=f', 'chipyaim=f',
	   ) or die "Try --help for more information.\n";
$opts{help} and _help();
$opts{version} and _version();

if ($opts{cgi} or $ENV{GATEWAY_INTERFACE}) {
  my $q = new CGI;
  $opts{$_} = $q->param($_) for $q->param;
  $opts{cgi} = 1;
  $^W = 0;
  $| = 1;

  $opts{dev} = '-/png' unless $opts{dev} =~ '-/(pdf|cps)';

  # if CGI environment and PNG/PostScript/PDF driver selected, then
  # we print the appropriate mime header
  if ($opts{dev} =~ m!/c?ps$!) {
    print $q->header('application/postscript');
  }
  elsif ($opts{dev} =~ m!/pdf$!) {
    print $q->header('application/pdf');
  }
  elsif ($opts{dev} =~ m!/t?png$!) {
    print $q->header('image/png');
  }
  else {
    print $q->header;
  }

}

if ($opts{dev} =~ m!-/pdf!) {
  open(STDOUT, '|/usr/bin/ps2pdf - -');
  $opts{dev} = '-/cps';
}

if ($opts{subarray}) {
  $opts{subarray} =~ m!^(?:1|1/2|1/4|1/8)$! or
    die "invalid subarray = '$opts{subarray}', valid values are 1, 1/2, 1/4 and 1/8\n";
}

$opts{grating} =~ /^(LETG|MEG|HEG)$/ or die "invalid grating='$opts{grating}', valid options are 'LETG', 'MEG' or 'HEG'\n";

my $zaimpoint = $opts{chipyaim} + $opts{zoffset} / ACIS_ARCSEC_PIX * 60;

my (@lines, @labels);

if (exists $opts{features}) {
  my ($labels, $wav) = extract_features($opts{features});
  @lines = @$wav;
  @labels = @$labels;
}
else {
  @labels = keys %default_features;
  @lines = values %default_features;
}

# empty labels become their wavelengh values
my @empty_index = grep {!length($labels[$_])} 0..$#labels;
@labels[@empty_index] = @lines[@empty_index] if @empty_index;

my ($ccd_width, $ccd_height, $ccd_gap, $ccd_n) = (1024, 1024, 18, 6);

init_plot($opts{dev}, $ccd_width, $ccd_height, $ccd_gap, $ccd_n);
pgscf(2);
draw_ccds($ccd_width, $ccd_height, $ccd_gap, $ccd_n, $opts{dither});


my @colors = (1)x@lines;
# C- blue, N- green, O- purple
for my $i (0..$#lines) {
  for ($labels[$i]) {
    ($_ eq 'C-Ly\ga' || $_ eq 'C-He\ga(r)' || $_ eq 'C-He\ga(f)')
      and $colors[$i] = 2, last;
    ($_ eq 'N-Ly\ga' || $_ eq 'N-He\ga(r)' || $_ eq 'N-He\ga(f)')
      and $colors[$i] = 6, last;
    ($_ eq 'O-Ly\ga' || $_ eq 'O-He\ga(r)' || $_ eq 'O-He\ga(f)')
      and $colors[$i] = 8, last;
    ($_ eq 'Ne-Ly\ga' || $_ eq 'Ne-He\ga(r)' || $_ eq 'Ne-He\ga(f)')
      and $colors[$i] = 7, last;
    ($_ eq 'Mg-Ly\ga' || $_ eq 'Mg-He\ga(r)' || $_ eq 'Mg-He\ga(f)')
      and $colors[$i] = 9, last;
    ($_ eq 'Si-Ly\ga' || $_ eq 'Si-He\ga(r)' || $_ eq 'Si-He\ga(f)')
      and $colors[$i] = 3, last;
    ($_ eq 'S-Ly\ga' || $_ eq 'S-He\ga(r)' || $_ eq 'S-He\ga(f)')
      and $colors[$i] = 10, last;
    ($_ eq 'Ar-Ly\ga' || $_ eq 'Ar-He\ga(r)' || $_ eq 'Ar-He\ga(f)')
      and $colors[$i] = 5, last;
    ($_ eq 'Ca-Ly\ga' || $_ eq 'Ca-He\ga(r)' || $_ eq 'Ca-He\ga(f)')
      and $colors[$i] = 11, last;
    ($_ eq 'Fe-Ly\ga' || $_ eq 'Fe-He\ga(r)' || $_ eq 'Fe-He\ga(f)')
      and $colors[$i] = 12, last;
  }
}

draw_lines(\@lines, \@labels, \@colors);

my $at = label_plot( 'ACIS-S / '.$opts{grating},
	    'SIM-Y offset = '.$opts{yoffset}."'",
#	    'SIM-Z offset = '.$opts{zoffset}."'",
	    'Redshift \fiz\fn = '.$opts{z},
	    'Dither full-amplitude = '.$opts{dither}.'"',
	    'Aimpoint CHIPX = '.$opts{chipxaim},
#	    'Subarray = '.$opts{subarray},
		     { size => 0.03, space => 0.04 }
	    );

#$at = label_plot( '', { size => 0.02, space => 0.03, at => $at });

$at = label_plot(
		 'C-Ly\ga, He\ga(r), He\ga(f)',
		 'N-Ly\ga, He\ga(r), He\ga(f)',
		 'O-Ly\ga, He\ga(r), He\ga(f)',
		 'Ne-Ly\ga, He\ga(r), He\ga(f)',
		 'Mg-Ly\ga, He\ga(r), He\ga(f)',
		 'Si-Ly\ga, He\ga(r), He\ga(f)',
		 'S-Ly\ga, He\ga(r), He\ga(f)',
		 'Ar-Ly\ga, He\ga(r), He\ga(f)',
		 'Ca-Ly\ga, He\ga(r), He\ga(f)',
		 'Fe-Ly\ga, He\ga(r), He\ga(f)',
		 { colors => [2,6,8,7,9,3,10,5,11,12], size => 0.02, space => 0.03, at => $at, lines => [(0)x3, (1)x3, (2)x3], }
		 );

# other lines listed
my @black_index = grep { length($labels[$_]) and $colors[$_] == 1 } 0..$#colors;
if (@black_index) {
  my $label = join ', ', @labels[@black_index];
  my @split_label = $label =~ /(.{0,75})/gs;
  $at = label_plot(@split_label, { size => 0.02, space => 0.03, at => $at });
}



uninit_plot();

exit 0;

sub _help {
  exec('perldoc', '-F', $FindBin::Bin . '/' . $FindBin::RealScript);
}

sub _version {
  print $version,"\n";
  exit 0;
}

sub uninit_plot { pgclos(); }

sub init_plot {
  my ($dev, $ccd_width, $ccd_height, $ccd_gap, $ccd_n) = @_;
  pgopen($dev) > 0 or die "could not open PGPLOT device '$dev'\n";


  if ($opts{swapbg}) {
    my ($fr, $fg, $fb);		# foreground RGB
    my ($br, $bg, $bb);		# background RGB
    pgqcr(0, $br, $bg, $bb);
    pgqcr(1, $fr, $fg, $fb);
    pgscr(0, $fr, $fg, $fb);
    pgscr(1, $br, $bg, $bb);
  }

  my $ccd_width_total = $ccd_width * $ccd_n + $ccd_gap * ($ccd_n - 1 );

  my $x_margin = 0;
  my $y_margin = 0.2;

  my $win_width = $ccd_width_total * (1 + 2 * $x_margin);
  my $win_height = $win_width * 8.5 / 11;

  # set window coords, adjust viewport for one-to-one aspect ratio
  pgwnad(
	 -$ccd_width_total * $x_margin,
	 $ccd_width_total * (1+$x_margin),
	 -$win_height*$y_margin,
	 $win_height*(1-$y_margin)
	 );

}

sub label_plot {

  my %opts = parse_opts(\@_, qw( colors at size space lines ) );

  my @lines = @_;

  pgsave();

  pgslw(2);

  my ($x1, $x2, $y1, $y2);
  pgqwin($x1, $x2, $y1, $y2);

  $opts{space} = 0.05 unless $opts{space};

  # left margin is 5% of window width
  my $xpos = $x1 + 0.05 * ($x2 - $x1);

  # top margin is 5% of window height
  my $yinc = ($y2-$y1) * $opts{space};
  my $ypos = exists $opts{at} ? $opts{at} : $y2-$yinc;

  # get text size, rescale it
  my ($xbox, $ybox);
  pgsch(1);
  pgqtxt(0, 0, 0, 0, 'ABC', $xbox, $ybox);
  $opts{size} = 0.04 unless $opts{size};
  my $char_height = $opts{size}; # fraction of window height we want characters to be
  pgsch($char_height * ($y2-$y1) / ($ybox->[1] - $ybox->[0]));

  for (0..$#lines) {
    $ypos -= $yinc;
    if ($opts{colors}) {
      pgsci($opts{colors}->[$_]);
    }
    pgtext($xpos, $ypos, $lines[$_]);
  }

  pgunsa();

  return $ypos;
}

sub draw_ccds {
  my ($ccd_width, $ccd_height, $ccd_gap, $ccd_n, $dither) = @_;
  my $ccd_width_total = $ccd_width * $ccd_n + ($ccd_gap * ($ccd_n-1));

  pgsave();

  # find out how large our text is, rescale character height accordingly
  my ($xbox, $ybox);
  pgsch(1);
  pgqtxt(0, 0, 0, 0, 'S0', $xbox, $ybox);
  my $char_height = 0.1; # fraction of CCD height we want characters to be
  pgsch($char_height * $ccd_height / ($ybox->[1] - $ybox->[0]));

  # set fill style to outline
  pgsfs(2);

  for my $i (1..$ccd_n) {
    my ($winx1, $winx2,
	$winy1, $winy2) = (
			   ($i-1)*($ccd_width+$ccd_gap) + 1,
			   ($i-1)*($ccd_width+$ccd_gap)+$ccd_width-1,
			   1,
			   $ccd_height
			   );
    # S1,S3 gets a light grey shade
    if ($i==4 or $i==2) {
      pgsave();
      pgsci(15);
      pgsfs(1); # solid fill style
      pgrect($winx1, $winx2, $winy1, $winy2);
      pgunsa();
    }
    pgrect($winx1, $winx2, $winy1, $winy2);

    if ($opts{subarray} ne '1') {
      my $ymargin;
      for ($opts{subarray}) {
	$_ eq '1/2' and $ymargin = (1024 - 512) / 2, last;
	$_ eq '1/4' and $ymargin = (1024 - 256) / 2, last;
	$_ eq '1/8' and $ymargin = (1024 - 128) / 2, last;
	die "invalid subarray = '$opts{subarray}'";
      }
      pgsave();
      pgsfs(2);
      pgrect($winx1, $winx2, $winy1+$ymargin, $winy2-$ymargin);
      pgsfs(3);
      pgrect($winx1, $winx2, 1, $ymargin);
      pgrect($winx1, $winx2, $winy2-$ymargin, $winy2);
      pgunsa();
    }

    pgsave();
    pgslw(2);
    pgtext(
	   $winx1+($winx2-$winx1)*0.1,
	   $winy1+($winy2-$winy1)*0.1,
	   '\frS'.($i-1).(($i==4 or $i == 2)? ' (BI)' : '')
	   );
    pgunsa();

    # draw dither amplitude on edges of detectors
    pgsave();
    pgsfs(1);
    pgscr(13, .5, .5, .5);
    pgsci(13);
    pgrect($winx1, $winx1+$dither/2/ACIS_ARCSEC_PIX, $winy1, $winy2);
    pgrect($winx2-$dither/2/ACIS_ARCSEC_PIX, $winx2, $winy1, $winy2);
    pgunsa();

  }

  my $subd = $opts{grating} eq 'LETG' ? 5 : 10;

  # draw restframe wavelength axis below chips
  pgslw(2);
  pgaxis('N',
	 0, -$ccd_height*0.1,
	 $ccd_width_total, -$ccd_height*0.1,
	 pix2wav(1), pix2wav($ccd_width_total),
	 10, $subd, -0.5, 0, 0.5, 1, 0
	 );

  my $rest_label = '\gl (\A)';
  $rest_label = 'Restframe ' . $rest_label if $opts{z};
  pgqtxt(0, 0, 0, 0, $rest_label, $xbox, $ybox);
  pgtext(wav2pix(0) - ($xbox->[2]-$xbox->[0])/2,
	 -$ccd_height*0.1 - ($ybox->[1]-$ybox->[0])*3,
	 $rest_label
	);

  # draw observed wavelength axis above chips
  if ($opts{z}) {
    my $obs_label = 'Observed \gl (\A)';
    pgaxis('N',
	   0, $ccd_height*1.1,
	   $ccd_width_total, $ccd_height*1.1,
	   pix2wav(1)*(1+$opts{z}), pix2wav($ccd_width_total)*(1+$opts{z}),
	   10, $subd, 0.5, 0, 0.5, -1, 0
	  );

    pgqtxt(0, 0, 0, 0, $obs_label, $xbox, $ybox);
    pgtext(wav2pix(0) - ($xbox->[2]-$xbox->[0])/2,
	   $ccd_height*1.1 + ($ybox->[1]-$ybox->[0])*2,
	   $obs_label
	  );
  }

    pgunsa();
}

sub draw_lines {

  my ($wav, $labels, $colors) = @_;

  my ($xbox, $ybox);

  # mark zeroeth order
  pgsave();
  my ($zerox, $zeroy) = wav2pix(0);
  pgpt(1, [$zerox], [$zeroy], 8);

  pgsls(1);

  pgscr(7, 0.9, 0.9, 0);

  for (0..$#{$wav}) {
    my ($wav, $label) = ($wav->[$_], $labels->[$_]);

    for my $wav ($wav, -$wav) {
      my ($x, $y) = wav2pix($wav);
      pgsci($colors->[$_]);
      pgline(2, [$x, $x], [256, 768]);
#      pgline(2, [$x, $x], [$y-30, $y+30]);

    }
  }
  pgunsa();
}

sub wav2pix_perfect {
  # rowland diameter, grating period and angle (mm, AA, deg)
  my ($d, $p, $a, $wav) = @_;

  return $wav * $d * 1e3 * cos($a*pi/180) / $p / ACIS_UM_PIX;
}

sub pix2wav_perfect {

  my ($d, $p, $a, $pix) = @_;

  return $pix * $p * ACIS_UM_PIX / $d / 1e3 / cos($a*pi/180);
}

{
  my ($wav, $pix);
  my $init;

  sub initwavpix {
    return if $init;

    $init = 1;

# below was how it was done prior to 2012...

#     $wav = [
#         -92.2060,      -64.0743,
#         -63.5533,      -35.4215,
#         -34.9005,      - 6.7688,
#         - 6.2478,       21.8840,
#          22.4050,       50.5367,
#          51.0578,       79.1895,
# 	   ];

#     $pix = [];
#     for (0..5) {
#       push @$pix, $_ * (1024 + 18) + 1;
#       push @$pix, $pix->[-1]+1023;
#     }

#     # the wavelengths above were supplied by Brad Wargelin in 2007, at that
#     # time the default aimpoint (no yoffset) was for chipx=224. If the
#     # the aimpoint moves to different coordinates (see $opts{chipxaim})
#     # we can correct for the difference here
#     my $diff = $opts{chipxaim} - 224;
#     $_ += $diff for @$pix;

#     $_ -= $opts{yoffset} * 60 / ACIS_ARCSEC_PIX for @$pix;


# ...but now Brad has changed everything up

#         CCD#         Y(LL)  Y(LR)   (all in mm)
#         CCD=4  S0  -81.090 -56.579
#         CCD=5  S1  -56.066 -31.554
#         CCD=6  S2  -31.052  -6.538
#         CCD=7  S3   -6.002  18.511
#         CCD=8  S4   18.987  43.500
#         CCD=9  S5   43.982  68.496

    $pix = [];
    for (0..5) {
      push @$pix, $_ * (1024 + 18) + 2;
      push @$pix, $pix->[-1]+1021;
    }

    my @pos = (
# from Brad's email, 2014-11-17, note these are in Ang rather than the previous mm
  -91.5827662,-63.4529883,
  -62.8642533,-34.7333241,
  -34.1572084,-6.0239851,
  -5.40885028, 22.7232249,
   23.2695009, 51.4015771,
   51.9547373, 80.087965,

	       #-81.090, -56.579,
	       #-56.066, -31.554,
	       #-31.052,  -6.538,
	       #-6.002,  18.511,
	       #18.987,  43.500,
	       #43.982,  68.496,
	       );

# Wavelength at chip location Y for a given pointing offset
#    = 1.147639*Y -0.027526*chipy0 + 6.929427 + 3.361665*Yoff

# where

# Y = edge (or any chip) location from table above (in mm)
# chipy0 = chipy coordinate for Yoffset=0 (set to 198)
# Yoff = Yoffset (pointing offset in arcmin)


    # if @pos are in mm units
    $wav = [
	    map {
	      LETG_P/LETG_D*$_ -0.027526*198 + 6.929427 + 3.361665*$opts{yoffset}
	    } @pos
	   ];

    # if @pos are in Ang units

    #
    # moved Yoffset=0 from chipx=198 to chipx=210 in Aug, 2016
    # $_ +=  LETG_P / LETG_D * ACIS_UM_PIX / 1e3 * (198-210) for @pos;

    # moved Yoffset=0 from chipx=210 to chipx=193.74 in Sept, 2022
    $_ +=  LETG_P / LETG_D * ACIS_UM_PIX / 1e3 * (198-$opts{chipxaim}) for @pos;

    $wav = [
	    map {
#	      $_ + 3.361665*$opts{yoffset}
	      $_ +  LETG_P / LETG_D * 60/ACIS_ARCSEC_PIX * ACIS_UM_PIX / 1e3 * $opts{yoffset}
	    } @pos
	   ];


    if ($opts{z}) {
      $_ /= 1+$opts{z} for @$wav;
    }

    if ($opts{grating} eq 'MEG') {
      $_ *=  MEG_P / LETG_P * LETG_D / MEG_D * cos(MEG_A * pi / 180) for @$wav;
    }
    elsif ($opts{grating} eq 'HEG') {
      $_ *= HEG_P / LETG_P * LETG_D / HEG_D * cos(HEG_A * pi / 180) for @$wav;
    }
  }

  sub pix2wav {
    initwavpix();
    return interpol($_[0], $pix, $wav);
  }

  sub wav2pix {
    initwavpix();
    my $xpix = interpol($_[0], $wav, $pix);

    return $xpix unless wantarray;

    # just forget about vertical positions for now
#    return $xpix, $zaimpoint;

    my $ypix = $zaimpoint;

    my $angle;
    for ($opts{grating}) {
      $_ eq 'MEG' and $angle = MEG_A, last;
      $_ eq 'HEG' and $angle = HEG_A, last;
      $_ eq 'LETG' and $angle = LETG_A, last;
      die;
    }

    $ypix += sin($angle * pi / 180) * ($xpix - interpol(0, $wav, $pix)) / cos($angle * pi / 180);
    return ($xpix, $ypix);
  }

}


sub interpol {
  my ($at, $x, $y) = @_;

  my ($x0, $x1, $y0, $y1);

  # indices to use in $x, $y array for linear interpolation
  my ($i0, $i1);

  if ($at < $x->[0]) {
    $i0 = 0;
    $i1 = 1;
  }
  elsif ($at >= $x->[-1]) {
    $i0 = -2;
    $i1 = -1;
  }

  for (1..@$x-1) {
    if ($at < $x->[$_]) {
      $i0 = $_-1;
      $i1 = $_;
      last;
    }
  }

  return $y->[$i0] +
    ($y->[$i1] - $y->[$i0]) / ($x->[$i1] - $x->[$i0]) * ($at-$x->[$i0]);

}

sub extract_features {
  my $s = shift;

  my (@name, @wav);

  my @f = split /;/, $s;

  # strip leading/trailing whitespace
  s/^\s+//g, s/\s+$//g for @f;

  @f = grep { length } @f;

  for (@f) {
    my ($name, $wav);
    /^(?:(.*?)\s+)?(-?\d+\.?\d*)$/ or die "invalid spectral feature = '$_'";
    push @name, $1;
    push @wav, $2;
  }

  return \(@name, @wav);
}

sub parse_opts {
  my $args = shift;

  my %opts = ();

  if (ref $args->[-1] eq 'HASH') {

    # copy hash, making keys lowercase as we go
    my $href_in = pop @$args;
    %opts = map { lc($_) => $href_in->{$_} } keys %$href_in;

    # ensure only allowed options are given
    if (@_) {

      # hash for convenient lookups of valid options
      my %allowed;
      @allowed{map lc, @_} = ();

      my $caller = (caller 1)[3] || 'main';
      exists $allowed{$_} or confess $caller."() - option '$_' unknown"
	for keys %opts;
    }
  }

  return %opts;
}
