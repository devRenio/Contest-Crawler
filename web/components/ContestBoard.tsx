import Link from "next/link";
import { fetchContests, type Contest } from "../lib/api";

const TABS = [
  { id: "all", label: "전체" },
  { id: "new", label: "새로 올라온" },
  { id: "closing", label: "마감임박" },
] as const;

const TAGS = ["", "hackathon", "AI", "data", "security", "startup", "idea"];

function ddayLabel(item: Contest): string {
  if (item.dday === null) return "일정 미확인";
  if (item.dday < 0) return "마감";
  if (item.dday === 0) return "D-Day";
  return `D-${item.dday}`;
}

export async function ContestBoard({
  tab,
  q,
  tag,
}: {
  tab: string;
  q: string;
  tag: string;
}) {
  let data: Awaited<ReturnType<typeof fetchContests>> | null = null;
  let error = "";
  try {
    data = await fetchContests(tab, q, tag);
  } catch (err) {
    error = err instanceof Error ? err.message : "오류";
  }

  return (
    <main className="wrap">
      <header className="hero">
        <h1>IT 공모전 보드</h1>
        <p>해커톤·경진대회와 대학생 아이디어 공모전을 모읍니다. <a href="/submit">제보하기</a></p>
      </header>

      <form className="toolbar" action="/contests">
        <div className="tabs">
          {TABS.map((item) => (
            <Link
              key={item.id}
              href={`/contests?tab=${item.id}${q ? `&q=${encodeURIComponent(q)}` : ""}${tag ? `&tag=${tag}` : ""}`}
              className={`tab${tab === item.id ? " on" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </div>
        <input className="search" name="q" defaultValue={q} placeholder="제목·주최 검색" />
        <input type="hidden" name="tab" value={tab} />
        <div className="filters">
          {TAGS.map((item) => (
            <Link
              key={item || "all-tags"}
              href={`/contests?tab=${tab}${q ? `&q=${encodeURIComponent(q)}` : ""}${item ? `&tag=${item}` : ""}`}
              className={`chip${(tag || "") === item ? " on" : ""}`}
            >
              {item === "idea" ? "아이디어" : item || "모든 태그"}
            </Link>
          ))}
        </div>
      </form>

      {error ? <p className="error">{error} API가 켜져 있는지 확인하세요.</p> : null}
      {data ? <p className="meta">{data.count}건</p> : null}

      {!error && data && data.items.length === 0 ? (
        <p className="empty">표시할 공모전이 없습니다. 수집을 한 번 실행해 보세요.</p>
      ) : null}

      <section className="grid">
        {data?.items.map((item) => (
          <article className="card" key={item.id}>
            <div className="badges">
              {item.is_new ? <span className="badge new">NEW</span> : null}
              {item.dday !== null && item.dday >= 0 && item.dday <= 14 ? (
                <span className="badge soon">{ddayLabel(item)}</span>
              ) : (
                <span className="badge">{ddayLabel(item)}</span>
              )}
              <span className="badge">{item.contest_type}</span>
              {item.tags.slice(0, 3).map((name) => (
                <span className="badge" key={name}>
                  {name}
                </span>
              ))}
            </div>
            <h2>{item.title}</h2>
            <div className="row">
              <span>{item.organizer || "주최 미확인"}</span>
              <span>{item.apply_end ? `${item.apply_end} 마감` : "일정 미확인"}</span>
            </div>
            <div className="actions">
              <a className="btn" href={item.apply_url} target="_blank" rel="noreferrer">
                원문 보기
              </a>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
