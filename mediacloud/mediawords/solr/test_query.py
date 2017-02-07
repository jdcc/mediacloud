from nose.tools import assert_raises
from nose.tools import assert_equals

from mediawords.solr.query import *


def normalize_tsquery(tsquery):
    """Normalize tsquery by lowercasing and normalizing spaces."""

    # make spaces around parentheses not significant
    tsquery = re.sub('\(', ' ( ', tsquery)
    tsquery = re.sub('\)', ' ) ', tsquery)

    # make multiple spaces not significant
    tsquery = re.sub('\s+', ' ', tsquery)

    tsquery = tsquery.lower()

    return tsquery


def validate_tsquery(solr_query, expected_tsquery):
    """Validate that the tsquery generated from the given solr query matches the expected tsquery."""

    got_tsquery = parse(solr_query).tsquery()

    assert_equals(normalize_tsquery(got_tsquery), normalize_tsquery(expected_tsquery))


def run_tsquery_tests():
    assert_raises(McSolrQueryParseSyntaxException, parse, "and")
    assert_raises(McSolrQueryParseSyntaxException, lambda x: parse(x).tsquery(), "media_id:1")
    assert_raises(McSolrQueryParseSyntaxException, parse, '"foo bar"~3')
    assert_raises(McSolrQueryParseSyntaxException, parse, '( foo bar )*')
    assert_raises(McSolrQueryParseSyntaxException, parse, '*')
    assert_raises(McSolrQueryParseSyntaxException, parse, '*foo')

    # single term
    validate_tsquery('foo', 'foo')
    validate_tsquery('( foo )', 'foo')

    # simple boolean
    validate_tsquery('foo and bar', '( foo  & bar )')
    validate_tsquery('( foo and bar )', '( foo & bar )')
    validate_tsquery('foo and bar and baz and bat', '( foo & bar & baz & bat )')
    validate_tsquery('foo bar', '( foo | bar )')
    validate_tsquery('( foo bar )', '( foo | bar )')
    validate_tsquery('( 1 or 2 or 3 or 4 )', '( 1 | 2 | 3 | 4 )')

    # more complex boolean
    validate_tsquery('foo and ( bar baz )', '( foo & ( bar | baz ) )')
    validate_tsquery('( foo or bat ) and ( bar baz )', '( ( foo | bat ) & ( bar | baz ) )')
    validate_tsquery('foo and bar and baz and bat and ( 1 2 3 )', '( foo & bar & baz & bat & ( 1 | 2 | 3 ) )')
    validate_tsquery('( ( ( a or b ) and c ) or ( d or ( f or ( g and h ) ) ) )',
                     '( ( ( a | b ) & c ) | d | f | ( g & h ) )')

    # not
    validate_tsquery('not ( foo bar )', '!( foo | bar )')
    validate_tsquery('!( foo and bar )', '!( foo & bar )')
    validate_tsquery('( foo -( bar and baz ) )', '( foo & !( bar & baz ) )')

    # phrase
    validate_tsquery('"foo bar-baz"', "( foo & bar & baz )")
    validate_tsquery('1 or 2 or "foo bar-baz"', "( 1 | 2 | ( foo & bar & baz ) )")
    validate_tsquery('( 1 or 2 or 3 ) and "foz fot"', "( ( 1 | 2 | 3 ) & ( foz & fot ) )")
    validate_tsquery('( 1 or 2 or 3 ) and !"foz fot"', "( ( 1 | 2 | 3 ) & !( foz & fot ) )")
    validate_tsquery('( 1 or 2 or "foo bar-baz" ) and "foz fot"', "( ( 1 | 2 | ( foo & bar & baz ) ) & ( foz & fot ) )")

    # strip fields and ranges
    validate_tsquery('media_id:1 and foo', "( foo )")
    validate_tsquery('baz and ( foo:( 1 2 3 ) and bar:[ 1 2 3 ] )', '( baz )')

    # +
    validate_tsquery('foo +bar baz', "( ( foo & bar ) | baz )")
    validate_tsquery('foo or +bar baz', "( foo | bar | baz )")
    validate_tsquery('+bar baz', "( bar | baz )")

    # wild card
    validate_tsquery('foo*', "foo:*")
    validate_tsquery('( foo* bar ) and baz*', "( ( foo:* | bar ) & baz:* )")

    # queries from actual topics
    candidate_query = "+( fiorina ( scott and walker ) ( ben and carson ) trump ( cruz and -victor ) kasich rubio (jeb and bush) clinton sanders ) AND (+publish_date:[2016-09-30T00:00:00Z TO 2016-11-08T23:59:59Z]) AND ((tags_id_media:9139487 OR tags_id_media:9139458 OR tags_id_media:2453107 OR tags_id_stories:9139487 OR tags_id_stories:9139458 OR tags_id_stories:2453107) ) "
    candidate_tsquery = "( ( fiorina | ( scott & walker ) | ( ben & carson ) | trump | ( cruz & !victor ) | kasich | rubio | ( jeb & bush ) | clinton | sanders ) )"
    validate_tsquery(candidate_query, candidate_tsquery)

    tp_query = '(      sentence:     (         "babies having babies" "kids having kids"         "children having children"         "teen mother" "teen mothers"         "teen father" "teen fathers"         "teen parent" "teen parents"         "adolescent mother" "adolescent mothers"         "adolescent father" "adolescent fathers"         "adolescent parent" "adolescent parents"         (              ( teenagers adolescent students "high school" "junior school" "middle school" "jr school" )             and             -( graduate and students )             and             ( pregnant pregnancy "birth rate" births )         )     )          or           title:     (          "kids having kids"         "children having children"         "teen mother" "teen mothers"         "teen father" "teen fathers"         "teen parent" "teen parents"         "adolescent mother" "adolescent mothers"         "adolescent father" "adolescent fathers"         "adolescent parent" "adolescent parents"         (              ( teenagers adolescent students "high school" "junior school" "middle school" "jr school" )             and             -( graduate and students )             and             ( pregnant pregnancy "birth rate" births )         )     ) )  and  (      tags_id_media:( 8878332 8878294 8878293 8878292 8877928 129 2453107 8875027 8875028 8875108 )     media_id:( 73 72 38 36 37 35 1 99 106 105 104 103 102 101 100 98 97 96 95 94 93 91 90 89 88                 87 86 85 84 83 80 79 78 77 76 75 74 71 70 69 68 67 66 65 64 63 62 61 60 59 58 57                 56 55 54 53 52 51 50 471694 42 41 40 39 34 33 32 31 30 24 23 22 21 20 18 13 12                  9 17 16 15 14 11 10 2 8 7 1150 6 19 29 28 27 26 25 65 4 45 44 43 ) )  and  publish_date:[2013-09-01T00:00:00Z TO 2014-09-15T00:00:00Z]  and  -language:( da de es fr zh ja tl id ro fi hu hr he et id ms no pl sk sl sw tl it lt nl no pt ro ru sv tr )'

    tp_tsquery = '( ( ( ( babies & having & babies ) | ( kids & having & kids ) | ( children & having & children ) | ( teen & mother ) | ( teen & mothers ) | ( teen & father ) | ( teen & fathers ) | ( teen & parent ) | ( teen & parents ) | ( adolescent & mother ) | ( adolescent & mothers ) | ( adolescent & father ) | ( adolescent & fathers ) | ( adolescent & parent ) | ( adolescent & parents ) | ( ( teenagers | adolescent | students | ( high & school ) | ( junior & school ) | ( middle & school ) | ( jr & school ) ) & !( graduate & students ) & ( pregnant | pregnancy | ( birth & rate ) | births ) ) ) ) )'

    validate_tsquery(tp_query, tp_tsquery)

    gg_query = ' (       gamergate* OR "gamer gate"      OR (          (                         ( (ethic* OR corrupt*) AND journalis* AND game*)                        OR ("zoe quinn" OR quinnspiracy OR "eron gjoni")                        OR (                            (misogyn* OR sexis* OR feminis* OR SJW*)                                AND (gamer* OR gaming OR videogam* OR "video games" OR "video game" OR "woman gamer" OR                                                 "women gamers" OR "girl gamer" OR "girl gamers")                        )                      OR (                            (game* OR gaming)                               AND (woman OR women OR female OR girl*)                                 AND (harass* OR "death threats" OR "rape threats")                      )                 )             AND -(espn OR football* OR "world cup" OR "beautiful game" OR "world cup" OR basketball OR "immortal game" OR                           "imitation game" OR olympic OR "super bowl" OR superbowl OR nfl OR "commonwealth games" OR poker OR sport* OR                           "panam games" OR "pan am games" OR "asian games" OR "warrior games" OR "night games" OR "royal games" OR                                "abram games" OR "killing the ball" OR cricket OR "game of thrones" OR "hunger games" OR "nomad games" OR "zero-sum game" OR                            "national game" OR fifa* OR "fa" OR golf OR "little league" OR soccer OR rugby OR lacrosse OR volleyball OR baseball OR                                 chess OR championship* OR "hookup culture" OR "popular culture" OR "pop culture" OR "culture of the game" OR                            "urban culture" OR (+minister AND +culture) OR stadium OR "ray rice" OR janay OR doping OR suspension OR glasgow OR "prince harry" OR                           courtsiding) ) )  AND +tags_id_media:(8875456 8875460 8875107 8875110 8875109 8875111 8875108 8875028 8875027 8875114 8875113 8875115 8875029 129 2453107 8875031 8875033 8875034 8875471 8876474 8876987 8877928 8878292 8878293 8878294 8878332 9028276)  AND +publish_date:[2014-06-01T00:00:00Z TO 2015-04-01T00:00:00Z]'

    gg_tsquery = '( ( gamergate:* | ( gamer & gate ) | ( ( ( ( ethic:* | corrupt:*) & journalis:* & game:*) | ( zoe & quinn ) | quinnspiracy | ( eron & gjoni ) | ( ( misogyn:* | sexis:* | feminis:* | SJW:*) & ( gamer:* | gaming | videogam:* | ( video & games ) | ( video & game ) | ( woman & gamer ) | ( women & gamers ) | ( girl & gamer ) | ( girl & gamers ) )  ) | ( ( game:* | gaming ) & ( woman | women | female | girl:*) & ( harass:* | ( death & threats ) | ( rape & threats ) )  ) ) & !( espn | football:* | ( world & cup ) | ( beautiful & game ) | ( world & cup ) | basketball | ( immortal & game ) | ( imitation & game ) | olympic | ( super & bowl ) | superbowl | nfl | ( commonwealth & games ) | poker | sport:* | ( panam & games ) | ( pan & am & games ) | ( asian & games ) | ( warrior & games ) | ( night & games ) | ( royal & games ) | ( abram & games ) | ( killing & the & ball ) | cricket | ( game & of & thrones ) | ( hunger & games ) | ( nomad & games ) | ( zero & sum & game ) | ( national & game ) | fifa:* | ( fa ) | golf | ( little & league ) | soccer | rugby | lacrosse | volleyball | baseball | chess | championship:* | ( hookup & culture ) | ( popular & culture ) | ( pop & culture ) | ( culture & of & the & game ) | ( urban & culture ) | (minister & culture ) | stadium | ( ray & rice ) | janay | doping | suspension | glasgow | ( prince & harry ) | courtsiding ) ) ) )'

    validate_tsquery(gg_query, gg_tsquery)

    coh_query = ' ( "culture of health" OR "culture of wellbeing" OR "culture of well being" OR "determinants of health" OR "health equity" OR "health equality" OR "health inequality" OR "health care access" OR "equal health" OR "healthy community" OR "healthy communities" OR "health prevention" OR "health promotion" OR (Disparities AND  ("infant mortality" OR cancer OR "heart disease" OR diabetes OR obesity OR "life expectancy" OR "low birth weight") ) OR (care AND underserved )  OR  ((health OR wellbeing OR "well-being") AND ("personal responsibility" OR "national priority" OR inequit* OR unequal OR injustice OR "zip code" OR disparities OR "opportunity gap" OR disadvantaged OR "unequal access" OR underserved OR poverty OR discrimin* OR "sexual orientation" OR "socioeconomic status" OR ( racist or racism ) OR ethnicity OR (minorit* and -leader* ))) )  AND (+publish_date:[2015-05-26T00:00:00Z TO 2016-05-26T23:59:59Z]) AND (((media_id:102836 OR media_id:285948) OR (tags_id_media:8875027 OR tags_id_media:2453107 OR tags_id_media:9139458 OR tags_id_media:8877008 OR tags_id_stories:8875027 OR tags_id_stories:2453107 OR tags_id_stories:9139458 OR tags_id_stories:8877008 or media_id:54174)))'

    coh_tsquery = '( ( ( culture & of & health ) | ( culture & of & wellbeing ) | ( culture & of & well & being ) | ( determinants & of & health ) | ( health & equity ) | ( health & equality ) | ( health & inequality ) | ( health & care & access ) | ( equal & health ) | ( healthy & community ) | ( healthy & communities ) | ( health & prevention ) | ( health & promotion ) | (Disparities &   (( infant & mortality ) | cancer | ( heart & disease ) | diabetes |  obesity | ( life & expectancy ) | ( low & birth & weight )) ) | (care & underserved )  |  ((health |  wellbeing | ( well & being )) & (( personal & responsibility ) | ( national & priority ) |  inequit:* |  unequal |  injustice | ( zip & code ) |  disparities | ( opportunity & gap ) |  disadvantaged | ( unequal & access ) |  underserved |  poverty |  discrimin:* | ( sexual & orientation ) | ( socioeconomic & status ) | racist |  racism |  ethnicity | (minorit:* & !leader:* ))) ) )'

    validate_tsquery(coh_query, coh_tsquery)

    school_query = '+( (("school climate" AND (difference OR disparit* OR gap OR discrim* OR equit* OR inequit* OR equal* OR inequal* OR unequal OR access OR care OR underserv* OR justice OR injustice OR pipeline)) OR (education AND pipeline) OR "suspension rate" OR "suspension rates" OR (("attention rate" OR "attention rates") AND -(olympics OR disney)) OR "parent involvement" OR "graduation rate" OR "dropout rate") AND ((tags_id_media:8875027 OR tags_id_media:2453107 OR tags_id_media:9139487 OR tags_id_media:9139458 OR tags_id_media:8875108 OR tags_id_media:8878293 OR tags_id_media:8878292 OR tags_id_media:8878294 OR tags_id_stories:8875027 OR tags_id_stories:2453107 OR tags_id_stories:9139487 OR tags_id_stories:9139458 OR tags_id_stories:8875108 OR tags_id_stories:8878293 OR tags_id_stories:8878292 OR tags_id_stories:8878294 OR tags_id_media:9188663)) ) AND (+publish_date:[2015-09-01T00:00:00Z TO 2016-09-01T23:59:59Z])'

    school_tsquery = '( ( ( ( school & climate )  & (difference | disparit:* | gap | discrim:* | equit:* | inequit:* | equal:* | inequal:* | unequal | access | care | underserv:* | justice | injustice | pipeline)) | (education & pipeline) | ( suspension & rate ) | ( suspension & rates ) | ((( attention & rate ) | ( attention & rates )) & !(olympics | disney)) | ( parent & involvement ) | ( graduation & rate ) | ( dropout & rate ) ) )'

    validate_tsquery(school_query, school_tsquery)

    lunch_query = ' +( (("head start" AND (food OR nutrition OR feed* OR breakfast OR lunch)) OR (WIC AND (school OR "pre school" OR "pre-school" OR "elementary" OR charter or "pre-k")) OR NSLP OR "national school lunch program" OR "Hunger-Free Kids Act" OR "School Breakfast Program" OR "Snack Program" OR "Child and Adult Care Food Program" OR "Summer Food Service Program") AND ((tags_id_media:8875027 OR tags_id_media:2453107 OR tags_id_media:9139487 OR tags_id_media:9139458 OR tags_id_media:8875108 OR tags_id_media:8878293 OR tags_id_media:8878292 OR tags_id_media:8878294 OR tags_id_stories:8875027 OR tags_id_stories:2453107 OR tags_id_stories:9139487 OR tags_id_stories:9139458 OR tags_id_stories:8875108 OR tags_id_stories:8878293 OR tags_id_stories:8878292 OR tags_id_stories:8878294 OR tags_id_media:9188663)) ) AND (+publish_date:[2015-09-01T00:00:00Z TO 2016-09-01T23:59:59Z])'

    lunch_tsquery = '((( ( head & start)  & (food | nutrition | feed:* | breakfast | lunch)) | (WIC & (school | ( pre  & school ) | ( pre & school ) | ( elementary ) | charter | ( pre & k ))) | NSLP | ( national & school & lunch & program ) | ( Hunger & Free & Kids & Act ) | ( School & Breakfast & Program ) | ( Snack & Program ) | ( Child & and & Adult & Care & Food & Program ) | ( Summer & Food & Service & Program ) ) )'

    validate_tsquery(lunch_query, lunch_tsquery)

    gender_query = ' +("gender equality" OR "gender inequality" OR "sexual inequality" OR misogyn* OR sexism OR sexist OR feminis* OR "sexual equality" OR "womens equality" OR "womens inequality" OR "sexual assault" OR "sexual harassment" OR "sex discrimination" OR "gender equity") AND +(US OR "united states" OR america*) AND +tags_id_media:(9237114 9268737 8875471 9237114 8875456 8875460 8875107 8875110 8875109 8875111 8875108 8875028 8875027 8875114 8875113 8875115 8875029 129 2453107 8875031 8875033 8875034 8875471 8876474 8876987 8877928 8878292 8878293 8878294 8878332) AND +publish_date:[2015-04-01T00:00:00Z TO 2016-10-31T00:00:00Z] AND -(tags_id_media:8876474 OR tags_id_media:9201395 OR tags_id_media:8876987)'

    gender_tsquery = '( ( ( gender & equality ) | ( gender & inequality ) | ( sexual & inequality ) | misogyn:* | sexism | sexist | feminis:* | ( sexual & equality )  | ( womens & equality ) | ( womens & inequality )  | ( sexual & assault ) | ( sexual & harassment ) | ( sex & discrimination ) | ( gender & equity )) & ( US | ( united & states ) | america:*) )'

    validate_tsquery(gender_query, gender_tsquery)


def normalize_re(s):
    """Normalize tsquery by lowercasing and normalizing spaces."""

    # make multiple spaces not significant
    s = re.sub('\s+', ' ', s)

    s = s.lower()

    return s


def validate_re(solr_query, expected_re):
    """Validate that the re generated from the given solr query matches the expected re."""

    got_re = parse(solr_query).re()

    assert_equals(normalize_re(got_re), normalize_re(expected_re))


def run_re_tests():
    # single term
    validate_re('foo', '[[:<:]]foo')
    validate_re('( foo )', '[[:<:]]foo')

    # simple boolean
    validate_re('foo and bar', '(?: (?: [[:<:]]foo .* [[:<:]]bar ) | (?: [[:<:]]bar .* [[:<:]]foo ) )')
    validate_re('( foo and bar )', '(?: (?: [[:<:]]foo .* [[:<:]]bar ) | (?: [[:<:]]bar .* [[:<:]]foo ) )')
    validate_re('foo and bar and baz and bat',
                '(?: (?: [[:<:]]foo .* (?: (?: [[:<:]]bar .* (?: (?: [[:<:]]baz .* [[:<:]]bat ) | (?: [[:<:]]bat .* [[:<:]]baz ) ) ) | (?: (?: (?: [[:<:]]baz .* [[:<:]]bat ) | (?: [[:<:]]bat .* [[:<:]]baz ) ) .* [[:<:]]bar ) ) ) | (?: (?: (?: [[:<:]]bar .* (?: (?: [[:<:]]baz .* [[:<:]]bat ) | (?: [[:<:]]bat .* [[:<:]]baz ) ) ) | (?: (?: (?: [[:<:]]baz .* [[:<:]]bat ) | (?: [[:<:]]bat .* [[:<:]]baz ) ) .* [[:<:]]bar ) ) .* [[:<:]]foo ) )')
    validate_re('foo bar', '(?: [[:<:]]foo | [[:<:]]bar )')
    validate_re('( foo bar )', '(?: [[:<:]]foo | [[:<:]]bar )')
    validate_re('( 1 or 2 or 3 or 4 )', '(?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 | [[:<:]]4 )')

    # more complex boolean
    validate_re('foo and ( bar baz )',
                '(?: (?: [[:<:]]foo .* (?: [[:<:]]bar | [[:<:]]baz ) ) | (?: (?: [[:<:]]bar | [[:<:]]baz ) .* [[:<:]]foo ) )')
    validate_re('( foo or bat ) and ( bar baz )',
                '(?: (?: (?: [[:<:]]foo | [[:<:]]bat ) .* (?: [[:<:]]bar | [[:<:]]baz ) ) | (?: (?: [[:<:]]bar | [[:<:]]baz ) .* (?: [[:<:]]foo | [[:<:]]bat ) ) )')
    validate_re('foo and bar and baz and bat and ( 1 2 3 )',
                '(?: (?: [[:<:]]foo .* (?: (?: [[:<:]]bar .* (?: (?: [[:<:]]baz .* (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) ) | (?: (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) .* [[:<:]]baz ) ) ) | (?: (?: (?: [[:<:]]baz .* (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) ) | (?: (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) .* [[:<:]]baz ) ) .* [[:<:]]bar ) ) ) | (?: (?: (?: [[:<:]]bar .* (?: (?: [[:<:]]baz .* (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) ) | (?: (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) .* [[:<:]]baz ) ) ) | (?: (?: (?: [[:<:]]baz .* (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) ) | (?: (?: (?: [[:<:]]bat .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) | (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]bat ) ) .* [[:<:]]baz ) ) .* [[:<:]]bar ) ) .* [[:<:]]foo ) )')
    validate_re('( ( ( a or b ) and c ) or ( d or ( f or ( g and h ) ) ) )',
                '(?: (?: (?: (?: [[:<:]]a | [[:<:]]b ) .* [[:<:]]c ) | (?: [[:<:]]c .* (?: [[:<:]]a | [[:<:]]b ) ) ) | [[:<:]]d | [[:<:]]f | (?: (?: [[:<:]]g .* [[:<:]]h ) | (?: [[:<:]]h .* [[:<:]]g ) ) )')

    # not claues should be filtered out
    # this should raise an error because filtering the not clause leaves an empty query
    assert_raises(McSolrQueryParseSyntaxException, lambda x: parse(x).re(), 'not ( foo bar )')
    validate_re('foo and !bar', '[[:<:]]foo')
    validate_re('foo -( bar and bar )', '[[:<:]]foo')

    # phrase
    validate_re('"foo bar-baz"', "[[:<:]]foo[[:space:]]+bar\-baz")
    validate_re('1 or 2 or "foo bar-baz"', "(?: [[:<:]]1 | [[:<:]]2 | [[:<:]]foo[[:space:]]+bar\-baz )")
    validate_re('( 1 or 2 or 3 ) and "foz fot"',
                "(?: (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) .* [[:<:]]foz[[:space:]]+fot ) | (?: [[:<:]]foz[[:space:]]+fot .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]3 ) ) )")
    validate_re('( 1 or 2 or "foo bar-baz" ) and "foz fot"',
                "(?: (?: (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]foo[[:space:]]+bar\-baz ) .* [[:<:]]foz[[:space:]]+fot ) | (?: [[:<:]]foz[[:space:]]+fot .* (?: [[:<:]]1 | [[:<:]]2 | [[:<:]]foo[[:space:]]+bar\-baz ) ) )")

    # queries from actual topics
    candidate_query = "+( fiorina ( scott and walker ) ( ben and carson ) trump ( cruz and -victor ) kasich rubio (jeb and bush) clinton sanders ) AND (+publish_date:[2016-09-30T00:00:00Z TO 2016-11-08T23:59:59Z]) AND ((tags_id_media:9139487 OR tags_id_media:9139458 OR tags_id_media:2453107 OR tags_id_stories:9139487 OR tags_id_stories:9139458 OR tags_id_stories:2453107) ) "
    candidate_re = "(?: [[:<:]]fiorina | (?: (?: [[:<:]]scott .* [[:<:]]walker ) | (?: [[:<:]]walker .* [[:<:]]scott ) ) | (?: (?: [[:<:]]ben .* [[:<:]]carson ) | (?: [[:<:]]carson .* [[:<:]]ben ) ) | [[:<:]]trump | [[:<:]]cruz | [[:<:]]kasich | [[:<:]]rubio | (?: (?: [[:<:]]jeb .* [[:<:]]bush ) | (?: [[:<:]]bush .* [[:<:]]jeb ) ) | [[:<:]]clinton | [[:<:]]sanders )"
    validate_re(candidate_query, candidate_re)

    tp_query = ' (      sentence:     (         "babies having babies" "kids having kids"         "children having children"         "teen mother" "teen mothers"         "teen father" "teen fathers"         "teen parent" "teen parents"         "adolescent mother" "adolescent mothers"         "adolescent father" "adolescent fathers"         "adolescent parent" "adolescent parents"         (              ( teenagers adolescent students "high school" "junior school" "middle school" "jr school" )             and             -( grad and students )             and             ( pregnant pregnancy "birth rate" births )         )     )          or           title:     (          "kids having kids"         "children having children"         "teen mother" "teen mothers"         "teen father" "teen fathers"         "teen parent" "teen parents"         "adolescent mother" "adolescent mothers"         "adolescent father" "adolescent fathers"         "adolescent parent" "adolescent parents"         (              (  adolescent students "high school" "junior school" "middle school" "jr school" )             and             -( foo )           and             ( pregnant pregnancy "birth rate" births )         )     ) )  and  (      tags_id_media:( 8878332 8878294 8878293 8878292 8877928 129 2453107 8875027 8875028 8875108 )     media_id:( 73 72 38 36 37 35 1 99 106 105 104 103 102 101 100 98 97 96 95 94 93 91 90 89 88                 87 86 85 84 83 80 79 78 77 76 75 74 71 70 69 68 67 66 65 64 63 62 61 60 59 58 57                 56 55 54 53 52 51 50 471694 42 41 40 39 34 33 32 31 30 24 23 22 21 20 18 13 12                  9 17 16 15 14 11 10 2 8 7 1150 6 19 29 28 27 26 25 65 4 45 44 43 ) )  and  publish_date:[2013-09-01T00:00:00Z TO 2014-09-15T00:00:00Z]  and  -language:( da de es fr zh ja tl id ro fi hu hr he et id ms no pl sk sl sw tl it lt nl no pt ro ru sv tr )'
    tp_re = '(?: (?: [[:<:]]babies[[:space:]]+having[[:space:]]+babies | [[:<:]]kids[[:space:]]+having[[:space:]]+kids | [[:<:]]children[[:space:]]+having[[:space:]]+children | [[:<:]]teen[[:space:]]+mother | [[:<:]]teen[[:space:]]+mothers | [[:<:]]teen[[:space:]]+father | [[:<:]]teen[[:space:]]+fathers | [[:<:]]teen[[:space:]]+parent | [[:<:]]teen[[:space:]]+parents | [[:<:]]adolescent[[:space:]]+mother | [[:<:]]adolescent[[:space:]]+mothers | [[:<:]]adolescent[[:space:]]+father | [[:<:]]adolescent[[:space:]]+fathers | [[:<:]]adolescent[[:space:]]+parent | [[:<:]]adolescent[[:space:]]+parents | (?: (?: (?: [[:<:]]teenagers | [[:<:]]adolescent | [[:<:]]students | [[:<:]]high[[:space:]]+school | [[:<:]]junior[[:space:]]+school | [[:<:]]middle[[:space:]]+school | [[:<:]]jr[[:space:]]+school ) .* (?: [[:<:]]pregnant | [[:<:]]pregnancy | [[:<:]]birth[[:space:]]+rate | [[:<:]]births ) ) | (?: (?: [[:<:]]pregnant | [[:<:]]pregnancy | [[:<:]]birth[[:space:]]+rate | [[:<:]]births ) .* (?: [[:<:]]teenagers | [[:<:]]adolescent | [[:<:]]students | [[:<:]]high[[:space:]]+school | [[:<:]]junior[[:space:]]+school | [[:<:]]middle[[:space:]]+school | [[:<:]]jr[[:space:]]+school ) ) ) ) )';

    validate_re(tp_query, tp_re)

    gg_query = ' (       gamergate* OR "gamer gate"      OR (          (                         ( (ethic* OR corrupt*) AND journalis* AND game*)                        OR ("zoe quinn" OR quinnspiracy OR "eron gjoni")                        OR (                            (misogyn* OR sexis* OR feminis* OR SJW*)                                AND (gamer* OR gaming OR videogam* OR "video games" OR "video game" OR "woman gamer" OR                                                 "women gamers" OR "girl gamer" OR "girl gamers")                        )                      OR (                            (game* OR gaming)                               AND (woman OR women OR female OR girl*)                                 AND (harass* OR "death threats" OR "rape threats")                      )                 )             AND -(espn OR football* OR "world cup" OR "beautiful game" OR "world cup" OR basketball OR "immortal game" OR                           "imitation game" OR olympic OR "super bowl" OR superbowl OR nfl OR "commonwealth games" OR poker OR sport* OR                           "panam games" OR "pan am games" OR "asian games" OR "warrior games" OR "night games" OR "royal games" OR                                "abram games" OR "killing the ball" OR cricket OR "game of thrones" OR "hunger games" OR "nomad games" OR "zero-sum game" OR                            "national game" OR fifa* OR "fa" OR golf OR "little league" OR soccer OR rugby OR lacrosse OR volleyball OR baseball OR                                 chess OR championship* OR "hookup culture" OR "popular culture" OR "pop culture" OR "culture of the game" OR                            "urban culture" OR (+minister AND +culture) OR stadium OR "ray rice" OR janay OR doping OR suspension OR glasgow OR "prince harry" OR                           courtsiding) ) )  AND +tags_id_media:(8875456 8875460 8875107 8875110 8875109 8875111 8875108 8875028 8875027 8875114 8875113 8875115 8875029 129 2453107 8875031 8875033 8875034 8875471 8876474 8876987 8877928 8878292 8878293 8878294 8878332 9028276)  AND +publish_date:[2014-06-01T00:00:00Z TO 2015-04-01T00:00:00Z]'

    gg_re = '(?: [[:<:]]gamergate | [[:<:]]gamer[[:space:]]+gate | (?: (?: (?: (?: [[:<:]]ethic | [[:<:]]corrupt ) .* (?: (?: [[:<:]]journalis .* [[:<:]]game ) | (?: [[:<:]]game .* [[:<:]]journalis ) ) ) | (?: (?: (?: [[:<:]]journalis .* [[:<:]]game ) | (?: [[:<:]]game .* [[:<:]]journalis ) ) .* (?: [[:<:]]ethic | [[:<:]]corrupt ) ) ) | [[:<:]]zoe[[:space:]]+quinn | [[:<:]]quinnspiracy | [[:<:]]eron[[:space:]]+gjoni | (?: (?: (?: [[:<:]]misogyn | [[:<:]]sexis | [[:<:]]feminis | [[:<:]]sjw ) .* (?: [[:<:]]gamer | [[:<:]]gaming | [[:<:]]videogam | [[:<:]]video[[:space:]]+games | [[:<:]]video[[:space:]]+game | [[:<:]]woman[[:space:]]+gamer | [[:<:]]women[[:space:]]+gamers | [[:<:]]girl[[:space:]]+gamer | [[:<:]]girl[[:space:]]+gamers ) ) | (?: (?: [[:<:]]gamer | [[:<:]]gaming | [[:<:]]videogam | [[:<:]]video[[:space:]]+games | [[:<:]]video[[:space:]]+game | [[:<:]]woman[[:space:]]+gamer | [[:<:]]women[[:space:]]+gamers | [[:<:]]girl[[:space:]]+gamer | [[:<:]]girl[[:space:]]+gamers ) .* (?: [[:<:]]misogyn | [[:<:]]sexis | [[:<:]]feminis | [[:<:]]sjw ) ) ) | (?: (?: (?: [[:<:]]game | [[:<:]]gaming ) .* (?: (?: (?: [[:<:]]woman | [[:<:]]women | [[:<:]]female | [[:<:]]girl ) .* (?: [[:<:]]harass | [[:<:]]death[[:space:]]+threats | [[:<:]]rape[[:space:]]+threats ) ) | (?: (?: [[:<:]]harass | [[:<:]]death[[:space:]]+threats | [[:<:]]rape[[:space:]]+threats ) .* (?: [[:<:]]woman | [[:<:]]women | [[:<:]]female | [[:<:]]girl ) ) ) ) | (?: (?: (?: (?: [[:<:]]woman | [[:<:]]women | [[:<:]]female | [[:<:]]girl ) .* (?: [[:<:]]harass | [[:<:]]death[[:space:]]+threats | [[:<:]]rape[[:space:]]+threats ) ) | (?: (?: [[:<:]]harass | [[:<:]]death[[:space:]]+threats | [[:<:]]rape[[:space:]]+threats ) .* (?: [[:<:]]woman | [[:<:]]women | [[:<:]]female | [[:<:]]girl ) ) ) .* (?: [[:<:]]game | [[:<:]]gaming ) ) ) ) )'

    validate_re(gg_query, gg_re)

    coh_query = ' ( "culture of health" OR "culture of wellbeing" OR "culture of well being" OR "determinants of health" OR "health equity" OR "health equality" OR "health inequality" OR "health care access" OR "equal health" OR "healthy community" OR "healthy communities" OR "health prevention" OR "health promotion" OR (Disparities AND  ("infant mortality" OR cancer OR "heart disease" OR diabetes OR obesity OR "life expectancy" OR "low birth weight") ) OR (care AND underserved )  OR  ((health OR wellbeing OR "well-being") AND ("personal responsibility" OR "national priority" OR inequit* OR unequal OR injustice OR "zip code" OR disparities OR "opportunity gap" OR disadvantaged OR "unequal access" OR underserved OR poverty OR discrimin* OR "sexual orientation" OR "socioeconomic status" OR ( racist or racism ) OR ethnicity OR (minorit* and -leader* ))) )  AND (+publish_date:[2015-05-26T00:00:00Z TO 2016-05-26T23:59:59Z]) AND (((media_id:102836 OR media_id:285948) OR (tags_id_media:8875027 OR tags_id_media:2453107 OR tags_id_media:9139458 OR tags_id_media:8877008 OR tags_id_stories:8875027 OR tags_id_stories:2453107 OR tags_id_stories:9139458 OR tags_id_stories:8877008 or media_id:54174)))'

    coh_re = '(?: [[:<:]]culture[[:space:]]+of[[:space:]]+health | [[:<:]]culture[[:space:]]+of[[:space:]]+wellbeing | [[:<:]]culture[[:space:]]+of[[:space:]]+well[[:space:]]+being | [[:<:]]determinants[[:space:]]+of[[:space:]]+health | [[:<:]]health[[:space:]]+equity | [[:<:]]health[[:space:]]+equality | [[:<:]]health[[:space:]]+inequality | [[:<:]]health[[:space:]]+care[[:space:]]+access | [[:<:]]equal[[:space:]]+health | [[:<:]]healthy[[:space:]]+community | [[:<:]]healthy[[:space:]]+communities | [[:<:]]health[[:space:]]+prevention | [[:<:]]health[[:space:]]+promotion | (?: (?: [[:<:]]disparities .* (?: [[:<:]]infant[[:space:]]+mortality | [[:<:]]cancer | [[:<:]]heart[[:space:]]+disease | [[:<:]]diabetes | [[:<:]]obesity | [[:<:]]life[[:space:]]+expectancy | [[:<:]]low[[:space:]]+birth[[:space:]]+weight ) ) | (?: (?: [[:<:]]infant[[:space:]]+mortality | [[:<:]]cancer | [[:<:]]heart[[:space:]]+disease | [[:<:]]diabetes | [[:<:]]obesity | [[:<:]]life[[:space:]]+expectancy | [[:<:]]low[[:space:]]+birth[[:space:]]+weight ) .* [[:<:]]disparities ) ) | (?: (?: [[:<:]]care .* [[:<:]]underserved ) | (?: [[:<:]]underserved .* [[:<:]]care ) ) | (?: (?: (?: [[:<:]]health | [[:<:]]wellbeing | [[:<:]]well\-being ) .* (?: [[:<:]]personal[[:space:]]+responsibility | [[:<:]]national[[:space:]]+priority | [[:<:]]inequit | [[:<:]]unequal | [[:<:]]injustice | [[:<:]]zip[[:space:]]+code | [[:<:]]disparities | [[:<:]]opportunity[[:space:]]+gap | [[:<:]]disadvantaged | [[:<:]]unequal[[:space:]]+access | [[:<:]]underserved | [[:<:]]poverty | [[:<:]]discrimin | [[:<:]]sexual[[:space:]]+orientation | [[:<:]]socioeconomic[[:space:]]+status | [[:<:]]racist | [[:<:]]racism | [[:<:]]ethnicity | [[:<:]]minorit ) ) | (?: (?: [[:<:]]personal[[:space:]]+responsibility | [[:<:]]national[[:space:]]+priority | [[:<:]]inequit | [[:<:]]unequal | [[:<:]]injustice | [[:<:]]zip[[:space:]]+code | [[:<:]]disparities | [[:<:]]opportunity[[:space:]]+gap | [[:<:]]disadvantaged | [[:<:]]unequal[[:space:]]+access | [[:<:]]underserved | [[:<:]]poverty | [[:<:]]discrimin | [[:<:]]sexual[[:space:]]+orientation | [[:<:]]socioeconomic[[:space:]]+status | [[:<:]]racist | [[:<:]]racism | [[:<:]]ethnicity | [[:<:]]minorit ) .* (?: [[:<:]]health | [[:<:]]wellbeing | [[:<:]]well\-being ) ) ) )'

    validate_re(coh_query, coh_re)

    school_query = '+( (("school climate" AND (difference OR disparit* OR gap OR discrim* OR equit* OR inequit* OR equal* OR inequal* OR unequal OR access OR care OR underserv* OR justice OR injustice OR pipeline)) OR (education AND pipeline) OR "suspension rate" OR "suspension rates" OR (("attention rate" OR "attention rates") AND -(olympics OR disney)) OR "parent involvement" OR "graduation rate" OR "dropout rate") AND ((tags_id_media:8875027 OR tags_id_media:2453107 OR tags_id_media:9139487 OR tags_id_media:9139458 OR tags_id_media:8875108 OR tags_id_media:8878293 OR tags_id_media:8878292 OR tags_id_media:8878294 OR tags_id_stories:8875027 OR tags_id_stories:2453107 OR tags_id_stories:9139487 OR tags_id_stories:9139458 OR tags_id_stories:8875108 OR tags_id_stories:8878293 OR tags_id_stories:8878292 OR tags_id_stories:8878294 OR tags_id_media:9188663)) ) AND (+publish_date:[2015-09-01T00:00:00Z TO 2016-09-01T23:59:59Z])'

    school_re = '(?: (?: (?: [[:<:]]school[[:space:]]+climate .* (?: [[:<:]]difference | [[:<:]]disparit | [[:<:]]gap | [[:<:]]discrim | [[:<:]]equit | [[:<:]]inequit | [[:<:]]equal | [[:<:]]inequal | [[:<:]]unequal | [[:<:]]access | [[:<:]]care | [[:<:]]underserv | [[:<:]]justice | [[:<:]]injustice | [[:<:]]pipeline ) ) | (?: (?: [[:<:]]difference | [[:<:]]disparit | [[:<:]]gap | [[:<:]]discrim | [[:<:]]equit | [[:<:]]inequit | [[:<:]]equal | [[:<:]]inequal | [[:<:]]unequal | [[:<:]]access | [[:<:]]care | [[:<:]]underserv | [[:<:]]justice | [[:<:]]injustice | [[:<:]]pipeline ) .* [[:<:]]school[[:space:]]+climate ) ) | (?: (?: [[:<:]]education .* [[:<:]]pipeline ) | (?: [[:<:]]pipeline .* [[:<:]]education ) ) | [[:<:]]suspension[[:space:]]+rate | [[:<:]]suspension[[:space:]]+rates | (?: [[:<:]]attention[[:space:]]+rate | [[:<:]]attention[[:space:]]+rates ) | [[:<:]]parent[[:space:]]+involvement | [[:<:]]graduation[[:space:]]+rate | [[:<:]]dropout[[:space:]]+rate )'

    validate_re(school_query, school_re)

    gender_query = ' +("gender equality" OR "gender inequality" OR "sexual inequality" OR misogyn* OR sexism OR sexist OR feminis* OR "sexual equality" OR "womens equality" OR "womens inequality" OR "sexual assault" OR "sexual harassment" OR "sex discrimination" OR "gender equity") AND +(US OR "united states" OR america*) AND +tags_id_media:(9237114 9268737 8875471 9237114 8875456 8875460 8875107 8875110 8875109 8875111 8875108 8875028 8875027 8875114 8875113 8875115 8875029 129 2453107 8875031 8875033 8875034 8875471 8876474 8876987 8877928 8878292 8878293 8878294 8878332) AND +publish_date:[2015-04-01T00:00:00Z TO 2016-10-31T00:00:00Z] AND -(tags_id_media:8876474 OR tags_id_media:9201395 OR tags_id_media:8876987)'

    gender_re = '(?: (?: (?: [[:<:]]gender[[:space:]]+equality | [[:<:]]gender[[:space:]]+inequality | [[:<:]]sexual[[:space:]]+inequality | [[:<:]]misogyn | [[:<:]]sexism | [[:<:]]sexist | [[:<:]]feminis | [[:<:]]sexual[[:space:]]+equality | [[:<:]]womens[[:space:]]+equality | [[:<:]]womens[[:space:]]+inequality | [[:<:]]sexual[[:space:]]+assault | [[:<:]]sexual[[:space:]]+harassment | [[:<:]]sex[[:space:]]+discrimination | [[:<:]]gender[[:space:]]+equity ) .* (?: [[:<:]]us | [[:<:]]united[[:space:]]+states | [[:<:]]america ) ) | (?: (?: [[:<:]]us | [[:<:]]united[[:space:]]+states | [[:<:]]america ) .* (?: [[:<:]]gender[[:space:]]+equality | [[:<:]]gender[[:space:]]+inequality | [[:<:]]sexual[[:space:]]+inequality | [[:<:]]misogyn | [[:<:]]sexism | [[:<:]]sexist | [[:<:]]feminis | [[:<:]]sexual[[:space:]]+equality | [[:<:]]womens[[:space:]]+equality | [[:<:]]womens[[:space:]]+inequality | [[:<:]]sexual[[:space:]]+assault | [[:<:]]sexual[[:space:]]+harassment | [[:<:]]sex[[:space:]]+discrimination | [[:<:]]gender[[:space:]]+equity ) ) )'

    validate_re(gender_query, gender_re)


def test_query():
    run_tsquery_tests()

    run_re_tests()
