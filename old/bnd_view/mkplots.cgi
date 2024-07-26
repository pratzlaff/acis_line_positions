#!/opt/local/bin/perl
#!/bin/sh --
#eval 'LD_LIBRARY_PATH=/opt/X11R6/lib;export LD_LIBRARY_PATH;exec /usr/bin/perl -x $0'
use strict;

$ENV{PGPLOT_FONT}="/home/rpete/local/pgplot/grfont.dat";
$ENV{PGPLOT_GIF_WIDTH}=650;

BEGIN {

	print "Content-type: image/gif\n\n";
	use CGI::Carp qw( carpout );
#	open(ERROR_LOG, ">>/home/rpete/www/base/error_log") or
#		die("error log problem: $!\n");
	open(ERROR_LOG, '>> /dev/null');
	carpout(\*ERROR_LOG);

	#
	# the following code is useful for making a plot offline
	# (don't forget to change $DEV below!
	#
=head1
	$ENV{QUERY_STRING} or do {
		open(F,"mkplots_input") or die $!;
		my @tmp=<F>; chop @tmp;
		$ENV{QUERY_STRING}=join('&',@tmp);
		close F;
		$ENV{REQUEST_METHOD}='GET';
	};
=cut
}

use Config;
use lib '/home/rpete/local/perlmods';
use lib '/home/rpete/local/perlmods/'.$Config{archname};
use PGPLOT qw(
	pgopen
	pgbbuf
	pgsubp
	pgscr
	pgpanl
	pgsvp
	pgsch
	pgmtxt
	pgebuf
	pgclos
	pgswin
	pgbox
	pgline
	pgbeg
	pgend
	pgtext
	pgsci
	pgsls
);

use CGI_Lite;
use Pg;
use MyMath;
$|=1;

my %det2pos=(
	'fpc_hn' => [1,1],
	'fpc_hs' => [1,2],
	'fpc_ht' => [1,3],
	'fpc_hb' => [1,4],
	'fpc_5'  => [2,1],
	'ssd_5'  => [2,2],
	'fpc_x1' => [2,3],
	'fpc_x2' => [2,3],
	'ssd_x'  => [2,3],
);

my $err_msg='';   # message to display in case of a problem
my $DEV='-/gif';
my $DATE;

my $q=new CGI_Lite;
my %FORM=$q->parse_form_data;

# get the 'window' parameters
my %VP=();
foreach ( qw(
	ssd_xlo
	ssd_xhi
	fpc_xlo
	fpc_xhi
	ssd_rlo
	ssd_rhi
	fpc_rlo
	fpc_rhi
) ) {
	($FORM{$_} =~ /^\d+$/) or
		error_routine("Parameter '$_' is not set properly");
	$VP{$_}=$FORM{$_};
}
($FORM{runid} =~ /^1\d{5}$/) or error_routine("Malformed runid");

#
# check the iterations supplied
#
my @iterations=split(/,/, $FORM{iterations});
foreach (@iterations) {
	/^\d+$/ or error_routine("Invalid iteration: '$_'");
}

#
# parameters that have to do with the look of the plot
#
my %PP = (
	'tch' => 3.0,  # character height for labels
	'nch' => 2.0,  # character height for axis numbers
	'xtitle' => '',
	'ytitle' => 'cnt s\u-1\d',
	'title' => '',
	'livetime' => 0.0,
);

make_plots($FORM{runid}) or error_routine($err_msg);
exit;

#
# make plots for each detector for a given runid
#
sub make_plots {
	my $R=shift;
	my %hash=get_phafiles($R) or return;    # get all files
	my $sumfile=$hash{'1'}->[0];
	verify_detector_iteration_numbers(%hash) or return; # are they in order?

	my @detnums=keys %hash; # list of all detector numbers
	my $nits=$#{$hash{$detnums[0]}}+1; # number of iterations
	unless (@iterations) { @iterations=(0..$nits-1) }
	my @new_its=();
	foreach (@iterations) { push @new_its, $_ if ($_ < $nits) }
	@iterations=@new_its or error_routine("No valid iterations given");

	pgopen($DEV) or die;
	pgbbuf();
	pgsubp(2,4);
	pgscr(0,1,1,1);
	pgscr(1,0,0,0);
	foreach my $n (keys %hash) {
		my $model_file=$hash{$n}[0];
		my %hdr=headpha($model_file) or return;
		my $nchan;
		($nchan=$hdr{channels}) or do {
			if ($hdr{detector} =~ /fpc/) { $nchan=512 }
			elsif ($hdr{detector} =~ /ssd/) { $nchan=4096 }
			else {
				$err_msg='Cannot find number of channels';
				return;
			}
		};
		my $detname=$hdr{detector} or do {
			$err_msg='Cannot get detector name';
			return;
		};
		exists $det2pos{$detname} or do {
			$err_msg="Detector '$detname' unrecognized";
			return;
		};
		$PP{title}=$detname.'(d'.$n.')';

		my @x=(0..$nchan-1);              # set up our arrays for plotting
		my @y=map(0,@x);
		$PP{livetime}=0.0;

		# add up all iterations
		my $base=substr($hash{$n}->[0],0,index($hash{$n}->[0],'i')+1);

		foreach my $it (@iterations) {
			my ($data,$hdr)=readpha($base.int($it).'.pha');
			defined $data or ($data,$hdr) = readpha($base.int($it).'.pha.gz');
			defined $data or error_routine($err_msg);
			$PP{livetime} += $hdr->{liveTime_sec} ? $hdr->{liveTime_sec} : 0.0;
			for (my $i=0; $i<$nchan; $i++) { $y[$i] += $data->[$i] }
		}
		$PP{title} .= sprintf(", livetime=%.2fs",$PP{livetime});
		my ($xlo,$xhi)=($detname =~ /fpc/) ?
			($VP{fpc_xlo},$VP{fpc_xhi}) : ($VP{ssd_xlo},$VP{ssd_xhi});
		my ($rlo,$rhi)=($detname =~ /fpc/) ?
			($VP{fpc_rlo},$VP{fpc_rhi}) : ($VP{ssd_rlo},$VP{ssd_rhi});

		pgpanl(@{$det2pos{$detname}});
		plotit(\@x,\@y,$xlo,$xhi,$rlo,$rhi,@{$det2pos{$detname}});
	}


	# get test parameters from first 'sum' file
	my %info=(
		'Runid' => $R,
		'TRW_ID'=> 'unknown',
		'Source' => 'unknown',
		'Energy' => 'unknown',
		'Type' => 'unknown',
		'Date' => $DATE,
	);
	GET_SUM_INFO: {
		$sumfile=substr($sumfile,0,index($sumfile,'acq'.$R)).$R.'d1.sum';
		open(SUM,$sumfile) or open(SUM,"/opt/local/bin/gunzip -c $sumfile.gz |") or last GET_SUM_INFO;
		while (<SUM>) {
			chop;
			last unless /^#/;
			my ($key,$value)=split /:\t/;
			$key=substr($key,1);
			if ($key eq 'uniqueId') { $info{Runid}=$value }
			elsif ($key eq 'srcType') { $info{Source}=$value }
			elsif ($key eq 'measureType') {
				foreach (split /,/, $value) {
					my ($key,$value)=split /:/;
					$info{$key}=$value;
				}
			}
		}
		close(SUM);
	}

	# now print test parameters
	pgpanl(2,4);
	pgsvp(0,1,0,1);
	pgsch(3*$PP{tch}/4);
	my $ytxt=1.0;
	foreach ( qw( Runid TRW_ID Type Source Energy Date ) ) {
		$ytxt -= 0.08;
		pgmtxt("LV",0,$ytxt,0,$_.":");
		pgmtxt("LV",-6,$ytxt,0,$info{$_});
	}
	$ytxt -= 0.08;
	pgmtxt("LV",0,$ytxt,0,"Iterations:");
	$ytxt += 0.08;
	my $xtxt;
	foreach my $i (0..$#iterations) {
		if ($i % 10 == 0) {
			$ytxt -= 0.08;
			$xtxt = -7;
		} else { $xtxt -= 3 }
		pgmtxt("LV",$xtxt,$ytxt,1.0,int($iterations[$i]));
	}

	pgebuf();
	pgclos();
	1;
}

# no error checking anywhere!
sub plotit {
	my ($xref,$yref,$xlo,$xhi,$rlo,$rhi)=@_;
	my ($min,$max) = min_max([@{$yref}[$xlo..$xhi]]);
	my $livetime=$PP{livetime};

	my $xopt="BCTSN";
	my $yopt=$xopt;

	my ($yhi,$ylo,$axis)=(($livetime > 0.0) ? 1/$livetime : $max+1.0,0,0);
	if ($max > 1) {
		$yhi=log10($max/$livetime);
		$ylo=log10(.8/$livetime);
		$yopt .= "L2";
	}

	# find sum of all counts in ROI
	map { $_=int $_ } ($rlo,$rhi);
	if ($rlo > $rhi) { my $t=$rlo; $rlo=$rhi; $rhi=$t }
	my $sum=MyMath::sum([@{$yref}[$rlo..$rhi]]);
	$PP{xtitle}='ROI=['.$rlo.','.$rhi.'], Sum='.$sum.' cnt';

	# Y axis becomes counts/sec
	if ($livetime > 0.0) {
		for (my $i=0; $i<=$#{$yref}; $i++) { $yref->[$i] /= $livetime }
	}
	log10_ref($yref);

	pgsch($PP{nch});       # set size of numbers on axis labels
	pgsvp(0.096,0.924,0.200,0.800); # set viewport size
	pgswin($xlo,$xhi,$ylo,$yhi);    # set axis limits
	pgbox($xopt,0,0,$yopt,0,0);     # make plot box

	# label axes
	pgsch($PP{tch});
	pgmtxt('T',.5,.5,.5,$PP{title});  # title
	pgmtxt('B',2.0,.5,.5,$PP{xtitle}); # X axis
	pgmtxt('L',1.5,.5,.5,$PP{ytitle}); # Y axis
	pgline(scalar @$xref,$xref,$yref);

	# plot lines around region of interest
	pgsls(2);
	pgsci(13);
	pgline(2,[$rlo,$rlo],[-1e20,1e20]);
	pgline(2,[$rhi,$rhi],[-1e20,1e20]);
	pgsls(1);
	pgsci(1);
	1;
}

#
# make sure all detectors have the same number of files
#
sub verify_detector_iteration_numbers {
	my %hash=@_;
	my @keys=keys %hash;
	my $n=$#{$hash{$keys[0]}};
	foreach (0..$#keys) {
		do {
			$err_msg='Files out of order';
			return;
		} unless ($#{$hash{$keys[$_]}} == $n);
	}
	return 1;
}

# return all pha files for a given runid
sub get_phafiles {
	my $R=shift;
	my $DIR=data_locale($R);
	return unless $DIR;
	opendir(DIR,$DIR) or do {
		$err_msg='Could not open data directory';
		return;
	};
	my @F=grep(/^acq${R}d[1-9]i[0-9]+\.pha(\.gz|)$/,readdir(DIR));
	closedir(DIR);
	do {
		$err_msg='No files found in data directory';
		return;
	} unless @F;

	my %hash=();
	foreach (@F) {
		push @{$hash{substr($_,10,1)}}, $DIR."/".$_;
	}
	return %hash;
}

# return data directory for a given runid
sub data_locale {
	my $R=shift;
	my $conn=Pg::connectdb("dbname=xrcf host=ascda3.cfa.harvard.edu");
	if ($conn->status != PGRES_CONNECTION_OK) {
		$err_msg="Could not connect to database: ".$conn->errorMessage;
		return;
	}
	my $result=$conn->exec("SELECT directory, date FROM trm WHERE runid = $R;");
	if (! $result->ntuples) {
		$err_msg="runid '$R' not found in database";
		return;
	}
	$DATE = $result->getvalue(0,1);

	my $dir = $result->getvalue(0,0);

	# they wiped the data from the head lan, have restored it to buffy
	$dir =~ s!^/data/hxds1!/data/buffy/hxds1!;
	return $dir;
}

# read pha header
sub headpha {
	my $F=shift;
	$F = "/opt/local/bin/gunzip -c $F |" if ($F =~ /\.gz$/);
	open(FH,$F) or do {
		$err_msg='Could not open PHA file';
		return;
	};
	my %hdr=();
	while (<FH>) {
		chop;
		last unless /^#/;
		my ($key,$value)=split /:\t/;
		$key=substr($key,1);
		$value =~ s/^\s*(.*?)\s*$/$1/ if $value;
		$hdr{$key}=$value;
	}
	$hdr{detector}=$_;
	close(FH);
	return %hdr;
}

#
# read pha data, return list ref
#
sub readpha {
	#
	# open file
	#
	my $F=shift;
	($F =~ /gz$/) and $F = "/opt/local/bin/gunzip -c $F |";
	open(FH,$F) or do {
		$err_msg='Could not open PHA file';
		return;
	};

	#
	# read header
	#
	my $hdr={};
	while (<FH>) {
		chop;
		last unless /^#/;
		my ($key,$value)=split /:\t/;
		$key=substr($key,1);
		$value =~ s/^\s*(.*?)\s*$/$1/ if $value;
		$hdr->{$key}=$value;
	}
	$hdr->{detector}=$_;
	<FH>;

	#
	# read data
	#
	my $data = [<FH>];
	close FH;
	chop @{$data};
	return ($data,$hdr);
}

sub min_max {
	my $ref=shift;
	my $min=$$ref[0];
	my $max=$min;
	foreach (@{$ref}) {
		$max=$_ if ($_ > $max);
		$min=$_ if ($_ < $min);
	}
	return ($min,$max);
}

# the obvious
sub log10 {
	my @output = map( (log($_)/2.30258509 ), @_);
	return $output[0];
}

# transform array to log10
sub log10_ref {
	my $ref=shift;
	for (my $i=0; $i<=$#{$ref}; $i++) {
		$ref->[$i] = ($ref->[$i] > 0) ? log($ref->[$i])/2.30258509 : -1e30;
	}
}

# an error was found, make image with message in it
sub error_routine {
	my $err_msg=shift;
	$ENV{PGPLOT_GIF_WIDTH}=800;
	$ENV{PGPLOT_GIF_HEIGHT}=30;
	pgbeg(0,$DEV,1,1);
	pgsch(45.0);
	pgtext(0,0,"Error: ".$err_msg);
	pgend();
	exit;
}
