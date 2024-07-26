#! /usr/bin/perl
use warnings;
use strict;

use Config;
use lib './build/perlmods';
use lib './build/perlmods/' . $Config{archname};

use CGI;
#use PGPLOT;

print CGI::header();

exec('/usr/bin/perl', '-V');
