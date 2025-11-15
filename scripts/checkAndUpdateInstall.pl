#!/usr/bin/perl

use strict;
use warnings;

use File::Copy qw(copy);

# This script validates the environment for running cluster-director-mcp by performing the following checks
# and taking remedial actions:
# - Checks and updates (if necessary) the path to the cluster-director-mcp binary
#   in ~/.gemini/settings.json and cluster-director-mcp/.gemini/extensions/cluster-director-mcp/gemini-extension.json
# - Checks and updates (if necessary) directories ~/.gemini and 
#   cluster-director-mcp/.gemini/extensions/cluster-director-mcp to ensure only one copy of 
#   scraped data from AI Hypercomputer is present in GEMINI.md files if they are present in both directories

use strict;

sub check_and_update_cluster_director_mcp_binary_path {
    my ($input_json_file, $mcp_binary_path) = @_;

    my $all_input_json_contents = "";
    my $bool_needs_replacement = 0;
    open(IF, $input_json_file) || die "Cannot open input JSON file for reading: $input_json_file";
    while (my $l = <IF>) {
        # This is the path to the cluster-director-mcp 
        if ($l =~ /command\:.*cluster-director-mcp\"/ && index($l, $mcp_binary_path) == -1) {
            # Sample line:
            # "command": "/usr/local/google/home/nadig/cluster-director-mcp-git-on-borg/new/cluster-director-mcp/cluster-director-mcp",
            $all_input_json_contents .= "\"command\": \"$mcp_binary_path\"";
            $bool_needs_replacement = 1;
        } else {
            $all_input_json_contents .= $l;
        }
    }
    close(IF);

    if ($bool_needs_replacement) {
        my $backup_json_file = "${input_json_file}.orig";
        copy($input_json_file, $backup_json_file) or die "File copy failed: $!";

        open(OF, ">$input_json_file") || die "Cannot write to file $input_json_file";
        print OF $all_input_json_contents;
        close(OF);

        print "Updated JSON to have correct path to cluster-director-mcp MCP binary: $input_json_file\n";
    } else {
        print "No update necessary to cluster-director-mcp MCP binary in $input_json_file\n";
    }
}

# Add the following lines
#   "mcpServers": {
#    "context7": {
#      "httpUrl": "https://mcp.context7.com/mcp"      
#    }
#  }
sub add_context7_mcp {
    my ($settings_json) = @_;

    open(IF, $settings_json) || die "Cannot open input JSON file for reading: $settings_json";
    my @lines = <IF>; # Read all lines
    close(IF);
    
    # Update only if context7 not there
    if (!grep(/context7/, @lines)) {
        my @addLines = ("\"mcpServers\": {\n",
                        "     \"context7\": {\n",
                        "           \"httpUrl\": \"https://mcp.context7.com/mcp\" \n",
                        "      }\n",
                        "},\n");
        my @outlines = ();
        # if there is already an mcpServer section
        if (grep(/mcpServers/, @lines)) {
            print "Input file already has mcpServers section : $settings_json\n";
            # only add lines with indices 1,2,3
            for my $line (@lines) {
                push (@outlines, $line);
                if ($line =~ /mcpServers/) {                    
                    push(@outlines, @addLines[1..3]);
                    push(@outlines, ",\n");
                }
            }
        } else {
            print "Input file does NOT have mcpServers section : $settings_json\n";
            my $doneInserting = 0;
            for my $line (@lines) {
                push (@outlines, $line);
                if ($line =~ /\{/ && !$doneInserting) {                    
                    push(@outlines, @addLines);
                    $doneInserting = 1;
                }
            }
        }

        my $outfile = "${settings_json}.out";
        open(OF, ">$outfile") || die "Cannot create outfile: $outfile";
        print OF join("", @outlines);
        close(OF);

        print "Wrote to temporary output : $outfile \n";
        my $save_json = "${settings_json}.orig";
        print "Saving original JSON as $save_json \n";
        copy($settings_json, $save_json) or die "File copy failed: $!";

        # now overwrite original json
        copy($outfile, $settings_json) or die "File copy failed: $!";

        print "Updated original JSON: $settings_json \n";
    }
    else {
        print "Input file already has context7 - no updates necessary: $settings_json\n"
    }    

}

############# Main #################

if (scalar @ARGV != 1) {
    die "Usage: $0 <cluster-director-mcp base dir>" . scalar(@ARGV)
}

my $base_dir  = shift @ARGV;
chdir $base_dir;

my $cd_mcp_bin = "$base_dir/cluster-director-mcp";
if (! -e $cd_mcp_bin) {
    print "Cluster Director MCP Binary does not exist: $cd_mcp_bin\n";
    print "Trying to run make....\n";
    system("make");
}

# Update JSON in CD directory
&check_and_update_cluster_director_mcp_binary_path("$base_dir/.gemini/extensions/cluster-director-mcp/gemini-extension.json", $cd_mcp_bin);

# Update JSON in Home directory
&check_and_update_cluster_director_mcp_binary_path("$ENV{HOME}/.gemini/extensions/cluster-director-mcp/gemini-extension.json", $cd_mcp_bin);

my $gemini_md_home = "$ENV{HOME}/.gemini/extensions/cluster-director-mcp/GEMINI.md";
my $gemini_md_git = "$base_dir/.gemini/extensions/cluster-director-mcp/GEMINI.md";

# Make proj GEMINI.md zero bytes
if (-e $gemini_md_home && -e $gemini_md_git) {
    if (-s $gemini_md_home == 0) {
        print "You have 2 GEMINI.md files for cluster-director-mcp - but the version in your home dir is 0 bytes. Not changing anything. \n";
        print "Path of GEMINI.md in your HOME: $gemini_md_home \n";
    } else {
        print "You have 2 GEMINI.md files for cluster-director-mcp - I will try to truncate one of them to 0 bytes to avoid loading duplicates of them \n";
        print "Home version: $gemini_md_home \n";
        print "Git version: $gemini_md_git \n";

        # Truncate home version - git is always newer
        truncate($gemini_md_home, 0);
    }
}

# 
&add_context7_mcp("$ENV{HOME}/.gemini/settings.json");

