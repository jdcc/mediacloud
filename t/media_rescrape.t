use strict;
use warnings;

BEGIN
{
    use FindBin;
    use lib "$FindBin::Bin/../lib";
    use lib $FindBin::Bin;
}

use Test::More tests => 59;
use Test::NoWarnings;
use Test::Deep;

use Modern::Perl "2013";
use MediaWords::CommonLibs;
use MediaWords::Test::DB;
use MediaWords::DBI::Media;

use HTTP::HashServer;
use Readonly;
use Data::Dumper;

# must contain a hostname ('localhost') because a foreign feed link test requires it
Readonly my $TEST_HTTP_SERVER_PORT => 9998;
Readonly my $TEST_HTTP_SERVER_URL  => 'http://localhost:' . $TEST_HTTP_SERVER_PORT;

Readonly my $PAGES_NO_FEEDS => {

    # Index page
    '/' => <<EOF,
        <h1>Acme News</h1>
        <p>
            Blah blah yada yada.
        </p>
        <hr />
        <p>
            This website doesn't have any RSS feeds, so it should be added
            as an "web_page" feed.
        </p>
EOF
};

Readonly my $PAGES_SINGLE_FEED_URL => $TEST_HTTP_SERVER_URL . '/feed.xml';
Readonly my $PAGES_SINGLE_FEED     => {

    # Index page
    '/' => <<"EOF",
        <html>
        <head>
            <link rel="alternate" href="$PAGES_SINGLE_FEED_URL" type="application/rss+xml" title="Acme News RSS feed" />
        </head>
        <body>
        <h1>Acme News</h1>
        <p>
            This website has a single feed that doesn't change after rescraping.
        </p>
        </body>
        </html>
EOF
    '/feed.xml' => {
        header  => 'Content-Type: application/rss+xml; charset=UTF-8',
        content => <<"EOF",
<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Acme News RSS feed</title>
                <link>$TEST_HTTP_SERVER_URL</link>
                <description>This is a sample RSS feed.</description>
                <item>
                    <title>First post</title>
                    <link>$TEST_HTTP_SERVER_URL/first.html</link>
                    <description>Here goes the first post in a sample RSS feed.</description>
                </item>
            </channel>
        </rss>
EOF
    }
};

# Media without any feeds
sub test_media_no_feeds($)
{
    my $db = shift;

    my $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_NO_FEEDS );
    $hs->start();

    # Create a test media that doesn't need rescraping
    Readonly my $urls_string => $TEST_HTTP_SERVER_URL;
    Readonly my $tags_string => '';
    my $medium = {
        name      => 'Acme News',
        url       => $TEST_HTTP_SERVER_URL,
        moderated => 'f',
    };
    $medium = $db->create( 'media', $medium );
    my $media_id = $medium->{ media_id };

    # Test the whole process two times to simulate initial scraping and rescraping
    for ( my $x = 0 ; $x < 2 ; ++$x )
    {

        MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );

        $medium = $db->find_by_id( 'media', $media_id );

        # say STDERR 'Medium: ' . Dumper( $medium );
        ok( $medium->{ moderated }, 'Media must be moderated after rescraping' );

        my $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ?', $media_id )->hashes;

        # say STDERR 'Feeds: ' . Dumper( $feeds );
        is( scalar( @{ $feeds } ), 1, 'Only a single feed must have been added' );
        my $webpage_feed = $feeds->[ 0 ];
        is( $webpage_feed->{ feed_type }, 'web_page',            "Single feed's type must be 'web_page'" );
        is( $webpage_feed->{ url },       $TEST_HTTP_SERVER_URL, "Single feed's URL must be test server" );

        my $feeds_after_rescraping =
          $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

        # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
        is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );

    }

    $hs->stop();
}

# Media with a single (thus automatically moderated) feed that doesn't change when rescraping
sub test_media_single_feed($)
{
    my $db = shift;

    my $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_SINGLE_FEED );
    $hs->start();

    # Create a test media that doesn't need rescraping
    Readonly my $urls_string => $TEST_HTTP_SERVER_URL;
    Readonly my $tags_string => '';
    my $medium = {
        name      => 'Acme News',
        url       => $TEST_HTTP_SERVER_URL,
        moderated => 'f',
    };
    $medium = $db->create( 'media', $medium );
    my $media_id = $medium->{ media_id };

    # Test the whole process two times to simulate initial scraping and rescraping
    for ( my $x = 0 ; $x < 2 ; ++$x )
    {

        MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );

        $medium = $db->find_by_id( 'media', $media_id );

        # say STDERR 'Medium: ' . Dumper( $medium );
        ok( $medium->{ moderated },
            "Media must be moderated after rescraping (because there was only a single feed added)" );

        my $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ?', $media_id )->hashes;

        # say STDERR 'Feeds: ' . Dumper( $feeds );
        is( scalar( @{ $feeds } ), 1, 'Only a single feed must have been added' );
        my $rss_feed = $feeds->[ 0 ];
        is( $rss_feed->{ feed_type }, 'syndicated',           "Single feed's type must be 'syndicated'" );
        is( $rss_feed->{ url },       $PAGES_SINGLE_FEED_URL, "Single feed's URL must match" );

        my $feeds_after_rescraping =
          $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

        # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
        is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );
    }

    $hs->stop();
}

# Media with a no feeds at initial scraping and a single feed after rescraping
sub test_media_no_feeds_then_single_feed($)
{
    my $db = shift;

    # Create a test media that doesn't need rescraping
    Readonly my $urls_string => $TEST_HTTP_SERVER_URL;
    Readonly my $tags_string => '';
    my $medium = {
        name      => 'Acme News',
        url       => $TEST_HTTP_SERVER_URL,
        moderated => 'f',
    };
    $medium = $db->create( 'media', $medium );
    my $media_id = $medium->{ media_id };

    #
    # Do initial scraping
    #
    my $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_NO_FEEDS );
    $hs->start();
    MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );
    $hs->stop();

    $medium = $db->find_by_id( 'media', $media_id );

    # say STDERR 'Medium: ' . Dumper( $medium );
    ok( $medium->{ moderated }, 'Media must be moderated after rescraping' );

    my $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds: ' . Dumper( $feeds );
    is( scalar( @{ $feeds } ), 1, 'Only a single feed must have been added' );
    my $webpage_feed = $feeds->[ 0 ];
    is( $webpage_feed->{ feed_type }, 'web_page',            "Single feed's type must be 'web_page'" );
    is( $webpage_feed->{ url },       $TEST_HTTP_SERVER_URL, "Single feed's URL must be test server" );

    my $feeds_after_rescraping = $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
    is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );

    #
    # Do rescraping (with a RSS feed now present)
    #
    $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_SINGLE_FEED );
    $hs->start();
    MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );
    $hs->stop();

    $medium = $db->find_by_id( 'media', $media_id );

    # say STDERR 'Medium: ' . Dumper( $medium );
    ok( $medium->{ moderated }, 'Media must be (still) moderated after rescraping' );

    $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ? ORDER BY feeds_id', $media_id )->hashes;

    # say STDERR 'Feeds: ' . Dumper( $feeds );
    is( scalar( @{ $feeds } ),
        2, 'Two feeds must be present (one for "web_page" feed created previously, another one just added)' );
    $webpage_feed = $feeds->[ 0 ];
    is( $webpage_feed->{ feed_type }, 'web_page',            "First feed's type must be 'web_page'" );
    is( $webpage_feed->{ url },       $TEST_HTTP_SERVER_URL, "First feed's URL must be test server" );
    is( $webpage_feed->{ feed_status }, 'inactive', "First feed should be deactivated (because we now have RSS feeds)" );

    my $rss_feed = $feeds->[ 1 ];
    is( $rss_feed->{ feed_type }, 'syndicated',           "Second feed's type must be 'syndicated'" );
    is( $rss_feed->{ url },       $PAGES_SINGLE_FEED_URL, "Second feed's URL must match" );

    $feeds_after_rescraping = $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
    is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );
}

# Media with a single feed at initial scraping and no feeds after rescraping
# (mimicking a scenario when a website is "down for maintenance" when
# rescraping)
sub test_media_single_feed_then_no_feeds_then_single_feed_again($)
{
    my $db = shift;

    # Create a test media that doesn't need rescraping
    Readonly my $urls_string => $TEST_HTTP_SERVER_URL;
    Readonly my $tags_string => '';
    my $medium = {
        name      => 'Acme News',
        url       => $TEST_HTTP_SERVER_URL,
        moderated => 'f',
    };
    $medium = $db->create( 'media', $medium );
    my $media_id = $medium->{ media_id };

    #
    # Do initial scraping (with a single feed being present)
    #
    my $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_SINGLE_FEED );
    $hs->start();
    MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );
    $hs->stop();

    $medium = $db->find_by_id( 'media', $media_id );

    # say STDERR 'Medium: ' . Dumper( $medium );
    ok( $medium->{ moderated }, "Media must be moderated after rescraping (because there was only a single feed added)" );

    my $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds: ' . Dumper( $feeds );
    is( scalar( @{ $feeds } ), 1, 'Only a single feed must have been added' );
    my $rss_feed = $feeds->[ 0 ];
    is( $rss_feed->{ feed_type }, 'syndicated',           "Single feed's type must be 'syndicated'" );
    is( $rss_feed->{ url },       $PAGES_SINGLE_FEED_URL, "Single feed's URL must match" );

    my $feeds_after_rescraping = $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
    is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );

    #
    # Do rescraping with no syndicated feeds being available now (for example,
    # the site is in the "maintenance mode" at the moment)
    #
    $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_NO_FEEDS );
    $hs->start();
    MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );
    $hs->stop();

    $medium = $db->find_by_id( 'media', $media_id );

    # say STDERR 'Medium: ' . Dumper( $medium );
    ok( $medium->{ moderated }, 'Media must be moderated after rescraping' );

    $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ? ORDER BY feeds_id', $media_id )->hashes;

    # say STDERR 'Feeds: ' . Dumper( $feeds );
    is( scalar( @{ $feeds } ),
        2, 'Two feeds must be present (one for "syndicated" feed created previously, another one ("web_page") just added)' );

    $rss_feed = $feeds->[ 0 ];
    is( $rss_feed->{ feed_type }, 'syndicated',           "First feed's type must be 'syndicated'" );
    is( $rss_feed->{ url },       $PAGES_SINGLE_FEED_URL, "First feed's URL must match" );

    my $webpage_feed = $feeds->[ 1 ];
    is( $webpage_feed->{ feed_type },   'web_page',            "Second feed's type must be 'web_page'" );
    is( $webpage_feed->{ url },         $TEST_HTTP_SERVER_URL, "Second feed's URL must be test server" );
    is( $webpage_feed->{ feed_status }, 'active',              "Second feed should be deactivated" );

    $feeds_after_rescraping = $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
    is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );

    #
    # Rescrape one last time, with syndicated feeds now being available once again
    #
    $hs = HTTP::HashServer->new( $TEST_HTTP_SERVER_PORT, $PAGES_SINGLE_FEED );
    $hs->start();
    MediaWords::DBI::Media::Rescrape::rescrape_media( $db, $media_id );
    $hs->stop();

    $medium = $db->find_by_id( 'media', $media_id );

    # say STDERR 'Medium: ' . Dumper( $medium );
    ok( $medium->{ moderated }, "Media must be moderated after rescraping (because there was only a single feed added)" );

    $feeds = $db->query( 'SELECT * FROM feeds WHERE media_id = ? ORDER BY feeds_id', $media_id )->hashes;

    # say STDERR 'Feeds: ' . Dumper( $feeds );
    is( scalar( @{ $feeds } ),
        2, 'Two feeds must be present (one for "syndicated" feed created previously, another one ("web_page") just added)' );

    $rss_feed = $feeds->[ 0 ];
    is( $rss_feed->{ feed_type }, 'syndicated',           "First feed's type must be 'syndicated'" );
    is( $rss_feed->{ url },       $PAGES_SINGLE_FEED_URL, "First feed's URL must match" );

    $webpage_feed = $feeds->[ 1 ];
    is( $webpage_feed->{ feed_type }, 'web_page',            "Second feed's type must be 'web_page'" );
    is( $webpage_feed->{ url },       $TEST_HTTP_SERVER_URL, "Second feed's URL must be test server" );
    is( $webpage_feed->{ feed_status },
        'inactive', "Second feed should be deactivated (because now RSS feeds are alive again)" );

    $feeds_after_rescraping = $db->query( 'SELECT * FROM feeds_after_rescraping WHERE media_id = ?', $media_id )->hashes;

    # say STDERR 'Feeds after rescraping: ' . Dumper( $feeds_after_rescraping );
    is( scalar( @{ $feeds_after_rescraping } ), 0, "'feeds_after_rescraping' table must be empty after rescraping" );
}

sub main()
{
    my @test_subroutines = (
        \&test_media_no_feeds,                                            #
        \&test_media_single_feed,                                         #
        \&test_media_no_feeds_then_single_feed,                           #
        \&test_media_single_feed_then_no_feeds_then_single_feed_again,    #
    );

    foreach my $test_subroutine_ref ( @test_subroutines )
    {
        MediaWords::Test::DB::test_on_test_database(
            sub {
                my $db = shift;

                $test_subroutine_ref->( $db );

                Test::NoWarnings::had_no_warnings();
            }
        );
    }
}

main();
