#!/opt/local/bin/perl
use strict;

#
# This program was written by Pete Ratzlaff, and is copyright 1998 by the
# Smithsonian Institution.
#

sub begin_html {
	print <<EOP;
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<HTML>
<HEAD>
<TITLE>CMDB Search</TITLE>
</HEAD>
<BODY>

EOP


#
# read include files, since CGI script output doesn't get processed by server
#
#<!--#include virtual="/incl/header.html"--> 
#
#<!--#include virtual="/incl/cal_h.html"--> 
#

open(FH,'/proj/web-cxc/htdocs/incl/header.html') or die;
print <FH>;
close FH;

open(FH,'/proj/web-cxc/htdocs/incl/cal_h.html') or die;
print <FH>;
close FH;

print <<EOP;
<BR>

<BLOCKQUOTE>

<H1>CMDB Search</H1>
EOP
	return 1;
}

sub end_html {
	print <<EOP;
This CGI program was written in <A HREF="http://www.perl.com">Perl</A>. You may
<A HREF="./cs.cgi?source">view the source</A>.

</BLOCKQUOTE>
<BR><BR>
<I>COMMENTS or ADDITIONS:</I>
<BR>
<A HREF="mailto:pratzlaff\@cfa.harvard.edu"><i>Pete Ratzlaff</i></a>


<!--PLEASE DO NOT MODIFY THIS LINE OR ANYTHING BELOW!-->

<br><br>

EOP

#
#<!--#include virtual="/incl/footer.html"--> 
#
open(FH,'/proj/web-cxc/htdocs/incl/footer.html') or die;
print <FH>;
close FH;

print <<EOP;
<!--footer end-->
 
</BODY>
</HTML> 
EOP
	return 1;
}

BEGIN {
	print "Content-type: text/html\n\n";
	begin_html();
	use CGI::Carp qw( carpout fatalsToBrowser );
#	open(ERROR_LOG,">>/home/rpete/www/base/error_log") or
#		die "error log problem: $!\n";
	open(ERROR_LOG,'>> /dev/null');
	carpout(\*ERROR_LOG);

=head1
	#
	# the following code is useful for running offline
	#
	$ENV{QUERY_STRING} or do {
		$ENV{QUERY_STRING}='';
		$ENV{REQUEST_METHOD}='GET';
	};
=cut

}

END {
	end_html();
}

use Config;
use lib '/home/rpete/local/perlmods';
use lib '/home/rpete/local/perlmods/'.$Config{archname};
use Pg;
use MyCGI_Lite;
use Benchmark;

#
# lame attempt at an error "stack"
#
my @ERRORS;

#
# @CMDB and %CMDB are list of all columns in CMDB
#
my @CMDB = <DATA>; chop @CMDB;
my %CMDB; @CMDB{@CMDB} = (0..$#CMDB);
my %CMDB_LC; @CMDB_LC{map(lc, @CMDB)} = (0..$#CMDB);

my (@COND,@COLUMN,@OP,@ARG,@GROUP_START,@GROUP_STOP); # used in SELECT command

my $q = new MyCGI_Lite;
#$q->logit;
my %FORM = $q->parse_form_data;

exists $FORM{source} and print_source();

#
# reset inputs if 'Clear' button pressed
#
exists $FORM{Clear} and @FORM{qw( query display )} = ('', '');

#
# clean up kruft in input fields
#
$FORM{query} = join("\n",verify_query_input());
$FORM{display} = join("\0",verify_display_input());
defined $FORM{testinfo} or $FORM{testinfo} = 0;
defined $FORM{rdb} or $FORM{rdb} = 0;

#
# make list of columns to display
#
my @DISPLAY = (length $FORM{display}) ? split("\0",$FORM{display}) : @CMDB[@CMDB_LC{@COLUMN}];
my $display_trw_id = grep( /trw_id/i, @DISPLAY );

#
# perform query
#
my $t0=time;
my ($conn,$result)=do_query();
my $QUERY_TIME = time() - $t0;

#
# finally, our output
#
print_errors();
print_query_output($conn,$result);
print_form();
exit;

#
# Returns list of all valid input query lines (from $FORM{query})
# Side effect of setting (@COLUMN,@COND,@OP,@ARG) arrays
#
sub verify_query_input {
	my @VALID;
	my @allowed_ops = qw( !~* !~~ ~~ !~ ~* != <= >= < > ~ = );
	foreach (split "\n", $FORM{query}) {
		s/^\s*(.*?)\s*$/$1/;
		length or next;
		/^(\(+)$/ and
			push(@GROUP_START,($#VALID+1-@GROUP_START-@GROUP_STOP)x(length $1)),
			push(@VALID, $_),
			next;
		/^(\)+)$/ and
			push(@GROUP_STOP,($#VALID-@GROUP_START-@GROUP_STOP)x(length $1)),
			push(@VALID, $_),
			next;
		my ($cond,$column,$op,$arg)=('AND',undef,'~*',undef);
		my $tmp=$_;
		$tmp =~ /^(AND|OR)\s*(.*)/i and ($cond, $tmp) = (uc($1),$2);
#		if ($tmp =~ /^(\w+)\s*(\Q!~*\E|\Q!~~\E|\Q~~\E|\Q!~\E|\Q~*\E|\Q!=\E|\Q<=\E|\Q<=\E|\Q>\E|\Q<\E|\Q~\E|=)\s*(.+?)$/) {
		if ($tmp =~ /^(\w+)\s*(${\(join('|',map(quotemeta($_), @allowed_ops)))})\s*(.+?)$/) {
			($column,$op,$arg)=($1,$2,$3);
		}
		elsif ($tmp =~ /^(\w+)\s+(.+?)$/) { # simplified input
			($column,$arg)=($1,$2);
		}
		else {
			push @ERRORS, "Could not parse query parameter '$_'";
			next;
		}
		if ($column =~ /^\d+$/) {
			if ($column > $#CMDB) {
				push @ERRORS, "CMDB column number '$column' is invalid (valid range is [0, $#CMDB])";
				next;
			}
			$column = lc $CMDB[$column];
		}
		else {
			exists $CMDB_LC{lc $column} or do {
				push @ERRORS, "CMDB column name '$column' is invalid";
				next;
			};
			$column = lc $column;
		}
		push @VALID, $_;
		push @COLUMN,$column;
		push @COND,$cond;
		push @OP,$op;

		$arg =~ s!\\!\\\\!g;
		$arg =~ s!'!\\'!g;
		push @ARG,$arg;
	}
		
	return @VALID;
}

#
# make array of columns to display
#
sub verify_display_input {
	my @output;
	foreach (split "\0", $FORM{display}) {
		exists $CMDB{$_} and push @output, $_; 
	}
	return @output;
}

sub do_query {
	return unless @COND;

	#
	# setup database connection
	#
	my $conn=Pg::connectdb("dbname=xrcf host=ascda3.cfa.harvard.edu");
	($conn->status == PGRES_CONNECTION_OK) or do {
		push @ERRORS, 'Could not connect to database: '.$conn->errorMessage;
		return;
	};

	#
	# make query string
	#
	my $string='SELECT '.join(',',@DISPLAY).(($display_trw_id) ? '' : ',TRW_ID').", datetime(date) AS dtdate FROM cmdb WHERE ".('('x(scalar grep($_ == 0, @GROUP_START)))." $COLUMN[0] $OP[0] '$ARG[0]' ".(')'x(scalar grep($_ == 0, @GROUP_STOP)));
	for (my $i=1; $i<@COND; $i++) {
		$string .= " $COND[$i] ".('('x(scalar grep($_ == $i, @GROUP_START)))." $COLUMN[$i] $OP[$i] '$ARG[$i]' ".(')'x(scalar grep($_ == $i, @GROUP_STOP)));
	}
	$string .= ' ORDER BY dtdate';
	print "<PRE><BLOCKQUOTE>$string</BLOCKQUOTE></PRE><BR>\n" if $FORM{showquery};

	my $result = $conn->exec($string);
	$conn->errorMessage and push @ERRORS, 'Error making query: '.$conn->errorMessage;

	return ($conn,$result);
}

sub print_query_output {
	return unless @COND;
	my ($conn,$result)=(shift,shift);

	print <<EOP;
<HR>
<H3>Query Results</H3>
EOP
	if (defined $result and $result->ntuples) {

		#
		# position of TRW_ID column in query results
		#
		my $trw_id_position;
		if (!$display_trw_id) { $trw_id_position = @DISPLAY }
		else {
			foreach (0..$#DISPLAY) {
				($DISPLAY[$_] =~ /^trw_id$/i) and do {
					$trw_id_position = $_;
					last;
				};
			}
		}

		#
		# get runids and acquisition dates if requested
		#
		my @RUNIDS = my @DATES = ();
		if ($FORM{testinfo}) {
			my $t0 = time();
			for (my $i=0; $i<$result->ntuples; $i++) {
				my $TRW_ID=$result->getvalue($i,$trw_id_position);
				my $query=$conn->exec("SELECT runid,date FROM trm WHERE trw_id = '$TRW_ID'");
				if ($query->ntuples < 1) {
					push @RUNIDS, 'Unknown';
					push @DATES, 'Unknown';
				}
				else {
					push @DATES, $query->getvalue(0,1);
					push @RUNIDS, join(',',map($query->getvalue($_,0), (0..$query->ntuples -1)));
				}
			}
			$QUERY_TIME += (time() - $t0);
		}
		print '<I>',$result->ntuples,"</I> matches found in $QUERY_TIME seconds<P>\n";

		#
		# output to RDB?
		#
		if ($FORM{rdb}) {
			print "<PRE>\n";
			if ($FORM{testinfo}) {
				print join("\t",@DISPLAY),"\tData_date\tRunids\n";
				print join("\t",map('-'x(length), @DISPLAY)),"\t---------\t------\n";
				my @tmp=(0..$#DISPLAY);
				for (my $i=0; $i<$result->ntuples; $i++) {
					print join("\t",(map($result->getvalue($i,$_),@tmp),$DATES[$i],$RUNIDS[$i])),"\n";
				}
			}
			else {
				print join("\t",@DISPLAY),"\n";
				print join("\t",map('-'x(length), @DISPLAY)),"\n";
				my @tmp=(0..$#DISPLAY);
				for (my $i=0; $i<$result->ntuples; $i++) {
					print join("\t",map($result->getvalue($i,$_),@tmp)),"\n";
				}
			}
			print "</PRE>\n";
			return 1;
		}

		print <<EOP;
<TABLE>
<TR align=center>
EOP
		foreach (@DISPLAY) { print "<TH>$_</TH>" }
		if (!$FORM{testinfo}) {
			print "<TH>More</TH>\n</TR>\n";
			for (my $i=0; $i<$result->ntuples; $i++) {
				print "<TR ALIGN=center>\n";
				for (my $j=0; $j<=$#DISPLAY; $j++) {
					print '<TD>'.$result->getvalue($i,$j)."</TD>\n";
				}
				print <<EOP;
<TD><A HREF="http://cxc.harvard.edu/cgi-gen/LETG/testinfo.cgi?tests=${\($result->getvalue($i,$trw_id_position))}">Go</A></TD>
</TR>
EOP
			}
		}
		else {
			print "<TH>Data_date</TH><TH>Runids</TH>\n</TR>\n";
			for (my $i=0; $i<$result->ntuples; $i++) {
				for (my $j=0; $j<=$#DISPLAY; $j++) {
					print '<TD>'.$result->getvalue($i,$j)."</TD>\n";
				}
				print "<TD>$DATES[$i]</TD><TD>$RUNIDS[$i]</TD>\n</TR>\n";
			}
		}
		print "</TABLE>\n";
	}
	else { print "No matches found for your query\n" }
	return 1;
}

sub print_form {
	print <<EOP;
<HR>
<form method="POST">
<TABLE>
<TR ALIGN=center><TH>Match Parameters</TH><TH>Output Parameters</TH></TR>
<TR VALIGN=top ALIGN=center>
<TD><TEXTAREA NAME="query" ROWS=5 COLS=30>$FORM{query}</TEXTAREA></TD>
<TD>
<SELECT NAME="display" SIZE=20 MULTIPLE>
EOP
	my %DIS;
	@DIS{split "\0", $FORM{display}} = ();
	for (my $i=0; $i<=$#CMDB; $i++) {
		my $col=$CMDB[$i];
		print
			"<OPTION VALUE=\"$col\"",
			((exists $DIS{$col}) ? ' SELECTED' : ''),
			">$i $col\n",
		;
	}
	print <<EOP;
</SELECT>
</TD>
</TR>
</TABLE><BR>
<INPUT TYPE="checkbox" NAME="testinfo" VALUE="1" ${\($FORM{testinfo} ? ' CHECKED' : '')}>
Display runids and data aquisition dates associated with each query match<BR>
<INPUT TYPE="checkbox" NAME="rdb" VALUE="1" ${\($FORM{rdb} ? ' CHECKED' : '')}>
Display output in RDB format?<BR>
<INPUT TYPE="checkbox" NAME="showquery" VALUE="1" ${\($FORM{showquery} ? ' CHECKED' : '')}>
Show SQL query being used (for debugging purposes)?<BR>
<INPUT TYPE="submit" NAME="Go" VALUE="Go">
<INPUT TYPE="submit" NAME="Clear" VALUE="Clear">
</FORM>
<HR>
<A HREF="http://cxc.harvard.edu/cal/Links/Letg/cmdb_search_help.html">Instructions for using this page</A>
<P>
EOP
	return 1;
}

sub print_errors {
	@ERRORS or return;
	print <<EOP;
<HR>
<H3>ERRORS</H3>
The following error messages were issued during your query:<BR> 
<BLOCKQUOTE><PRE>
EOP
	print join("\n",@ERRORS),"\n";
	print <<EOP;
</PRE></BLOCKQUOTE>
Contact <A HREF="mailto:pratzlaff\@cfa.harvard.edu">Pete Ratzlaff</A> if you
think it would help.
EOP
	return 1;
}

#
# outputs source code for this scripts
#
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

__DATA__
TRW_ID
Date
Submitted_by
Measurement_config
Measurement_type
Suite_no
Item
X_Ray_source_choices
X_Ray_energy
X_Ray_target_line
X_Ray_source_voltage
X_Ray_mono_initial
X_Ray_mono_res_power
X_Ray_mono_range
X_Ray_mono_step_size
X_Ray_source_flux
Filter_mat_1
Filter_thick_1
Filter_mat_2
Filter_thick_2
BND_choice
HRMA_pitch
HRMA_yaw
HRMA_rel_T
Gratings
Shutters
HRC_shutter
Focal_plane_choice
SIM_Z
ACIS_readmode
ACIS_frametime
ACIS_proc_mode
ACIS_Temp
HXDA_defocus
HXDA_Y
HXDA_Z
HXDA_Y_range
HXDA_Y_step
HXDA_Z_range
HXDA_Z_step
HXDA_number_aperts
HXDA_aperts
HXDA_beam_center
Number_locs
Locs
Five_axis_choice
Five_axis_x
Five_axis_y
Five_axis_z
Five_axis_roll
Five_axis_pitch
Five_axis_yaw
Integration_time
Time_Based_On
Atomic_time
Multiplicity
Test_Priority
Link_name
Block
Sequence_block_rank
Repeat
HRC_mcp_hv_upper
HRC_mcp_hv_lower
HRC_electronics
HRC_discrim_upper
HRC_discrim_trigger
HRC_blanking_mode
HRC_blanking_coords
HRC_pmt_hv
HRC_pmt_choice
HRC_door
HRC_cal_source
HRC_puls_gen
ACIS_image_loc_id
ACIS_block_checksum
ACIS_bias_id
HXDA_SSD_shape
HXDA_FPC_gas
X_ray_spot_size
X_ray_source_current
X_ray_source_param
Suite_file_address
HXDA_BND_status_code
HXDA_num_iter
HXDA_iter_time
Rate_Counts
Back_Bias
ACIS_num_rows
ACIS_num_setup_frames
ACIS_num_data_frames
ACIS_tdbfile
Grating_orders
