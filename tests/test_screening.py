from scriptorium.reasoning.screening import screen, ScreenCriteria
from scriptorium.sources.base import Paper


def _p(year=2020, lang="en", title="", abstract=""):
    return Paper(paper_id="X", source="openalex", title=title, authors=[],
                 year=year, abstract=abstract, raw={"language": lang})


def test_drop_for_year_lower_bound():
    res = screen(_p(year=2010), ScreenCriteria(year_min=2015))
    assert res.keep is False
    assert "year" in res.reason


def test_drop_for_year_upper_bound():
    res = screen(_p(year=2024), ScreenCriteria(year_max=2020))
    assert res.keep is False


def test_drop_for_language():
    res = screen(_p(lang="fr"), ScreenCriteria(languages=["en"]))
    assert res.keep is False
    assert "language" in res.reason


def test_drop_for_required_keyword_absent():
    res = screen(_p(title="A study", abstract="No relevant terms"),
                 ScreenCriteria(must_include=["caffeine"]))
    assert res.keep is False
    assert "must_include" in res.reason


def test_drop_for_excluded_keyword_present():
    res = screen(_p(title="Animal study of caffeine in rats", abstract="x"),
                 ScreenCriteria(must_exclude=["rats"]))
    assert res.keep is False


def test_keep_when_all_pass():
    res = screen(
        _p(year=2020, lang="en", title="Caffeine and working memory", abstract="adults"),
        ScreenCriteria(year_min=2015, languages=["en"],
                       must_include=["caffeine"], must_exclude=["rats"])
    )
    assert res.keep is True
    assert res.reason == "all criteria pass"


def test_undated_paper_fails_year_min_but_passes_year_max():
    """year=None fails a floor bound but passes a ceiling bound (intentional asymmetry)."""
    assert screen(_p(year=None), ScreenCriteria(year_min=2015)).keep is False
    assert screen(_p(year=None), ScreenCriteria(year_max=2020)).keep is True
