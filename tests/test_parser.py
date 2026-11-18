#----------------------------------
#	Tests / HTML parsing module
#----------------------------------

from spider.parser import extract_urls


BASE = "https://site.test/dir/page.html"


#--------------
#	PUBLIC
#--------------

def test_img_relative_src_is_resolved():
	images, _ = _parse('<img src="pic.jpg"><img src="/root.png"><img src="../up.gif">')
	assert images == {
		"https://site.test/dir/pic.jpg",
		"https://site.test/root.png",
		"https://site.test/up.gif",
	}


def test_link_to_image_goes_to_images_not_pages():
	images, pages = _parse('<a href="photo.JPEG">x</a>')
	assert images == {"https://site.test/dir/photo.JPEG"}
	assert pages == set()


def test_link_to_page_goes_to_pages():
	images, pages = _parse('<a href="other.html">x</a>')
	assert images == set()
	assert pages == {"https://site.test/dir/other.html"}


def test_extension_check_ignores_query_string():
	images, _ = _parse('<img src="pic.png?w=200">')
	assert images == {"https://site.test/dir/pic.png?w=200"}


def test_unsupported_extension_is_ignored():
	images, _ = _parse('<img src="vector.svg"><img src="photo.webp">')
	assert images == set()


def test_dangerous_and_useless_schemes_are_ignored():
	body = (
		'<a href="javascript:alert(1)">a</a>'
		'<a href="mailto:x@y.z">b</a>'
		'<a href="tel:0600000000">c</a>'
		'<a href="#top">d</a>'
		'<img src="data:image/png;base64,AAAA">'
		'<a href="ftp://site.test/f.jpg">e</a>'
		'<a href="file:///etc/passwd">f</a>'
	)
	images, pages = _parse(body)
	assert images == set()
	assert pages == set()


def test_missing_or_empty_attributes_do_not_crash():
	images, pages = _parse('<img><img src=""><img src="   "><a>no href</a><a href="">x</a>')
	assert images == set()
	assert pages == set()


def test_protocol_relative_url_takes_page_scheme():
	images, _ = _parse('<img src="//cdn.test/a.jpg">')
	assert images == {"https://cdn.test/a.jpg"}


def test_base_href_changes_resolution():
	images, pages = _parse('<base href="https://other.test/x/"><img src="a.jpg"><a href="p.html">p</a>')
	assert images == {"https://other.test/x/a.jpg"}
	assert pages == {"https://other.test/x/p.html"}


def test_invalid_base_href_is_ignored():
	images, _ = _parse('<base href="javascript:void(0)"><img src="a.jpg">')
	assert images == {"https://site.test/dir/a.jpg"}


def test_malformed_html_does_not_crash():
	images, _ = _parse('<div><img src="a.jpg"<p><a href="b.html"')
	assert isinstance(images, set)


#--------------
#	PRIVATE
#--------------

def _parse(body: str) -> tuple[set[str], set[str]]:
	return extract_urls(body.encode(), BASE)
