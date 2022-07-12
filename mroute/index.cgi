#!/usr/bin/perl
use strict;

require "./config.cgi";

my @rtrs = getRtrs();
my ($sshuser, $sshpass) = getUserPass();
my $tempdir = getTempDir();
mkdir($tempdir) unless (-d $tempdir);


my $dnsCache = {};
my $mcast = {};
my $didRefresh = {};
my $intDB = {};

my %flagDB = (
"D" => "Dense",
"S" => "Sparse",
"B" => "Bidir Group",
"s" => "SSM Group",
"C" => "Connected",
"L" => "Local",
"P" => "Pruned",
"R" => "RP-bit set",
"F" => "Register flag",
"T" => "SPT-bit set",
"J" => "Join SPT",
"M" => "MSDP created entry",
"E" => "Extranet",
"X" => "Proxy Join Timer Running",
"A" => "Candidate for MSDP Advertisement",
"U" => "URD",
"I" => "Received Source Specific Host Report",
"Z" => "Multicast Tunnel",
"z" => "MDT-data group sender",
"Y" => "Joined MDT-data group",
"y" => "Sending to MDT-data group",
"G" => "Received BGP C-Mroute",
"g" => "Sent BGP C-Mroute",
"N" => "Received BGP Shared-Tree Prune",
"n" => "BGP C-Mroute suppressed",
"q" => "Sent BGP S-A Route",
"v" => "Vector",
"p" => "PIM Joins on route",
"x" => "VxLAN group",
"c" => "PFP-SA cache created entry"
    );

# return a (cached) dns name
sub revDns($) {
    my ($ip) = @_;
    my $dns = `host "$ip"`;
    $dns =~ s/.*domain name pointer //;
    if ($dns =~ /NXDOMAIN/) {
        return "";
    }
    $dns = cleanDNS($dns);
    $dns =~ s/[\. ]*$//;
    return "$dns";
}

# Return a shrothand interface
sub displayNameInt($$) {
    my ($rtr, $int) = @_;
    $int =~ s/TenGigabitEthernet/Te/;
    $int =~ s/GigabitEthernet/Gi/;
    $int =~ s/Vlan/Vl/;
    return $int;
}

sub rtrIntDesc($$) {
    my ($rtr, $int) = @_;
    if ($intDB->{$rtr}->{$int}) {
        return $intDB->{$rtr}->{$int}->{desc};
    }
    return $int;
}

sub decodeFlags($) {
    my ($_flags) = @_;
    my @flags = split(//, $_flags);
    my $out = "";
    foreach (@flags) {
        $out .= "$_ - ".%flagDB{$_}."\n";
    }
    return $out;
}



my $plainoutput = "";

foreach my $rtr (sort @rtrs) {
    $plainoutput .= "=== $rtr ===\n\n";
    my $src = "";
    my $group = "";
    my $inOutList = 0;
    
    my $fn_int = "$tempdir/int-$rtr";

    my($mtime) = (stat("$fn_int"))[9];
    my $age = time - $mtime;
    $plainoutput .= "$rtr interface cache Age = $age\n";
    $didRefresh->{$rtr}->{interface}->{age} = $age;
    $didRefresh->{$rtr}->{interface}->{refreshed} = 0;
    if ($age > 1800) {
        $plainoutput .= "$rtr interface cache refresh\n";
        $didRefresh->{$rtr}->{interface}->{refreshed} = 1;
        open(R, "sshpass -p $sshpass ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $sshuser\@$rtr \"show int desc\"|");
        open(W, ">$fn_int");
        while(<R>) { print W; }
        close(R);
        close(W);
    }

    open(R, "$fn_int");
    while(<R>) {
        s/[\r\n]//g;
        s/\s\s\s\s\s*/;/g;
        my ($int, $state, $proto, $desc) = split(/;/);
    #    print "$int == $desc\n";;
        $intDB->{$rtr}->{$int}->{desc} = $desc;
    }
    close(R);


    my $fn_mrte = "$tempdir/mroute-$rtr";
    my($mtime) = (stat("$fn_mrte"))[9];
    my $age = time - $mtime;
    $plainoutput .= "$rtr mroute Age = $age\n";

    $didRefresh->{$rtr}->{mroute}->{age} = $age;
    $didRefresh->{$rtr}->{mroute}->{refreshed} = 0;
    if ($age > 30) {
        $plainoutput .= "$rtr mroute cache refresh\n";
        $didRefresh->{$rtr}->{mroute}->{refreshed} = 1;
        open(R, "sshpass -p $sshpass ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $sshuser\@$rtr \"show ip mroute\"|");
        open(W, ">$fn_mrte");
        while(<R>) { print W; }
        close(R);
        close(W);
    }

    open(R, "$fn_mrte");
    while(<R>) {
        s/[\r\n]//g;
        if (/^\(([0-9\.\*]+), ([0-9\.]+)\), ([^ ]*).*flags: (.*)/) {
            $src = $1;
            $group = $2;
            $mcast->{$group}->{$src}->{$rtr}->{time} = $3;
            $mcast->{$group}->{$src}->{$rtr}->{flags} = $4;
        }
        if (/Incoming interface: ([^,]*)/) {
            $mcast->{$group}->{$src}->{$rtr}->{incomingint} = $1;
        }
        if (/Outgoing interface list: Null/) {
            $mcast->{$group}->{$src}->{$rtr}->{outgoingint} = qw//;
        } elsif (/Outgoing interface list:/) {
            $mcast->{$group}->{$src}->{$rtr}->{outgoingint} = qw//;
            $inOutList = 1;
        }
        if ($inOutList) {
            if (/^\s*([^,]*), ([^,]*), ([^ ]*)/) {
                $mcast->{$group}->{$src}->{$rtr}->{outgoingint}->{$1}->{name} = $1;
                $mcast->{$group}->{$src}->{$rtr}->{outgoingint}->{$1}->{state} = $2;
                $mcast->{$group}->{$src}->{$rtr}->{outgoingint}->{$1}->{time} = $3;
            }
        }
        if (/^$/) {
            $src = "";
            $group = "";
            $inOutList = 0;
        }
        $plainoutput .= "$rtr: $_\n";
    }
    close(R);
} 


my $rtrs = "";
foreach my $rtr (sort @rtrs) {
    my $mrte_r = $didRefresh->{$rtr}->{mroute}->{refreshed};
    my $intf_r = $didRefresh->{$rtr}->{interface}->{refreshed};

    my $title = "";
    if ($intf_r == 0) { $title .= "Interfaces cached for " . $didRefresh->{$rtr}->{interface}->{age} . "s. "; }
    if ($mrte_r == 0) { $title .= "Mroute cached for " . $didRefresh->{$rtr}->{mroute}->{age} . "s. "; }
    if ($title eq "") { $title = "Fully refreshed"; }

    $rtrs .= "<span title='$title'>$rtr</span> ";
}

print "Content-Type: text/html\n\n";

print <<EOH

<html>
<head>
<style>
span {
    text-decoration: red double underline ;
    cursor: pointer;
}
</style>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/jquery.tablesorter/2.31.0/css/theme.default.min.css'>
<script type='text/javascript' src='https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js'></script>
<script type='text/javascript' src='https://cdnjs.cloudflare.com/ajax/libs/jquery.tablesorter/2.31.0/js/jquery.tablesorter.min.js'></script>
<script type='text/javascript' src='https://cdnjs.cloudflare.com/ajax/libs/jquery.tablesorter/2.31.0/js/jquery.tablesorter.widgets.min.js'></script>
<script src='mroute.js'></script> 
</head>
<body>
<h1>BCN Multicast Spy</h1>
Scanned: $rtrs

<table border id='list'>
<thead>
<tr><th>Group</th><th>Source IP</th><th>Incoming interfaces</th><th>Outgoing interfaces</th><th>Time</th><th>Flags</th></tr>
</thead>
<tbody>
EOH
;

foreach my $group (sort keys %{$mcast}) {
    my $groupname = revDns($group);
    foreach my $src (sort keys %{$mcast->{$group}}) {
        my $srcname = revDns($src);
        my $srcdisp = "$src ($srcname)";
        if ($src == "*") {
            $srcdisp = "*";
        }
        print "<tr>";
        print "<td>$group ($groupname)</td>";
        print "<td>$srcdisp</td>";
        print "<td>"; # incoming interfaces
        foreach my $rtr (sort keys %{$mcast->{$group}->{$src}}) {
            my $disprtr = displayNameRouter($rtr);
            my $int = $mcast->{$group}->{$src}->{$rtr}->{incomingint};
            my $desc = rtrIntDesc($rtr, displayNameInt($rtr, $int));
            my $dispint = "<span title='$desc'>" . displayNameInt($rtr, $int) . "</span>";
            print "$disprtr: $dispint<br>\n";
        }
        print "</td>"; # incoming interfaces
        print "<td>"; # outgoing interfaces
        foreach my $rtr (sort keys %{$mcast->{$group}->{$src}}) {
            my $desc = "$rtr\n\n";
            my $disprtr = displayNameRouter($rtr);
            my $dispint = "";
            my $int = $mcast->{$group}->{$src}->{$rtr}->{outgoingint};
            if (defined($int)) {
                $dispint = "";
                foreach my $oint (sort keys %{$int}) {
                    $desc .= displayNameInt($rtr, $oint)." :: ".rtrIntDesc($rtr, displayNameInt($rtr, $oint))."\n";
                    $dispint .= displayNameInt($rtr, $oint).",";
#                    $dispint .= "<span title='$desc'>".displayNameInt($rtr, $oint)."</span>,";
                }
                $dispint =~ s/,$//;
            }
            #print "$disprtr: $dispint<br>\n";
            if ("" eq $dispint) { $desc .= "No outgoing interfaces"; }
            print "<span title='$desc'>$disprtr: $dispint</span><br>\n";
        }
        print "</td>"; # outgoing interfaces

        # Time
        print "<td>"; # Time
        foreach my $rtr (sort keys %{$mcast->{$group}->{$src}}) {
            my $disprtr = displayNameRouter($rtr);
            my $time = $mcast->{$group}->{$src}->{$rtr}->{time};
            print "$disprtr:$time<br>\n";
        }
        print "</td>"; # Time

        # Flags
        print "<td>"; # Flags
        foreach my $rtr (sort keys %{$mcast->{$group}->{$src}}) {
            my $disprtr = displayNameRouter($rtr);
            my $flags = $mcast->{$group}->{$src}->{$rtr}->{flags};
            my $decFlag = "$rtr\n\n".decodeFlags($flags);
            print "<span title='$decFlag'>$disprtr:$flags</span><br>\n";
        }
        print "</td>"; # Flags
    }
}

print <<EOF
</tbody>
</table>
</body>
</html>

EOF
;


