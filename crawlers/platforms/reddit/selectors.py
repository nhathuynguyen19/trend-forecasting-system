"""Selectors for Reddit."""

# Listing container
LISTING = (
    "div#siteTable, "
    "div.thing, "
    "shreddit-post"
)


# Old Reddit
PRIMARY_THING = (
    "div#siteTable > div.thing.link, "
    "div.thing.link"
)

FALLBACK_THING = (
    "div#siteTable > div.thing, "
    "div.thing"
)


# Post fields
TITLE = (
    "a.title, "
    "a[data-click-id='body']"
)

AUTHOR = (
    "a.author, "
    "a[data-testid='post_author_link']"
)

SCORE = (
    "div.score.unvoted, "
    "div.score"
)

COMMENTS = (
    "a.comments, "
    "a.bylink.comments"
)

BODY = (
    "div.usertext-body div.md"
)


# Pagination
NEXT_BUTTON = (
    "span.next-button a"
)