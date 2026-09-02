from collector.adapters.campuspick import parse_activities
from collector.adapters.thinkyou import parse_ajax
from collector.adapters.wevity import parse_list

WEVITY = """
<div class="ms-list">
<ul class="list">
<li>
  <div class="tit">
    <a href="?c=find&s=1&gbn=view&gp=1&ix=110675">제3회 미래융합인재 발굴 소프트웨어 챌린지</a>
    <div class="sub-tit">분야 : 웹/모바일/IT, 게임/소프트웨어</div>
  </div>
  <div class="organ">과학기술정보통신부</div>
  <div class="day">D-35 <span class="dday ing">접수중</span></div>
</li>
</ul>
</div>
"""

THINKYOU = """
<div class="board_list contest">
<div class="tr">
  <div class="title">
    <a href="/contest/66352/">
      <dl><dt><h3>2026 뉴스빅데이터 해커톤</h3></dt>
      <dd>주최 : 한국언론진흥재단</dd></dl>
    </a>
  </div>
  <div class="etc">26-08-24 ~ 26-09-17</div>
  <div class="statNew"><p class="icon receiving">접수중</p>D-14</div>
</div>
</div>
"""


def test_wevity_parse_list():
    items = parse_list(WEVITY)
    assert len(items) == 1
    assert items[0].source_id == "110675"
    assert "소프트웨어" in items[0].title


def test_thinkyou_parse_ajax():
    items = parse_ajax(THINKYOU, "IT/SW")
    assert len(items) == 1
    assert items[0].source_id == "66352"
    assert items[0].apply_end.isoformat() == "2026-09-17"


def test_campuspick_parse_activities():
    payload = {
        "status": "success",
        "result": {
            "activities": [
                {
                    "id": 35919,
                    "title": "2026 뉴스빅데이터 해커톤",
                    "endDate": "2026-09-17",
                    "company": "한국언론진흥재단",
                    "categories": [101, 108],
                }
            ]
        },
    }
    items = parse_activities(payload)
    assert len(items) == 1
    assert items[0].source_name == "campuspick"
    assert items[0].source_id == "35919"
    assert items[0].organizer == "한국언론진흥재단"
    assert "contest/view?id=35919" in items[0].source_url
    assert items[0].apply_end.isoformat() == "2026-09-17"
