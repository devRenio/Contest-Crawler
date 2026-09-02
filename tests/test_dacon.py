from collector.adapters.dacon import parse_competitions

DACON = """
<div class="comp">
  <a href="/competitions/official/236749/overview/" class="clearfix">
    <div class="desc">
      <p class="name ellipsis">딥보이스 범죄 대응을 위한 AI 탐지 모델 경진대회</p>
      <p class="info2 ellipsis keyword"><span>알고리즘 | 오디오</span></p>
    </div>
    <div class="etc"><div class="dday">참가신청중</div></div>
  </a>
</div>
"""


def test_dacon_parse():
    items = parse_competitions(DACON)
    assert len(items) == 1
    assert items[0].source_id == "236749"
    assert items[0].status_hint == "open"
