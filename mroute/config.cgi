#!/usr/bin/perl
use strict;

my @rtrs = qw/rtr1 rtr2/;
my $sshpass = "secretepass";
my $sshuser = "limiteduser";
my $tempdir = "/var/tmp/mroute";

sub getRtrs { return @rtrs; }
sub getUserPass { return ($sshuser, $sshpass); }
sub getTempDir { return $tempdir; }
sub cleanDNS($) {
    my ($dns) = @_;
    $dns =~ s/.mydomain.com.//;
    return $dns;
} 

# Return a shorthand for the router name
sub displayNameRouter($) {
    my ($rtr) = @_;
    return "R1" if ($rtr eq "my-router-1");
    return "R2" if ($rtr eq "my-router-2");
    return $rtr;
}

