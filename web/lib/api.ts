export type Contest = {
  id: string;
  title: string;
  organizer: string;
  contest_type: string;
  tags: string[];
  eligibility: string;
  apply_start: string | null;
  apply_end: string | null;
  apply_url: string;
  source_url: string;
  source_name: string;
  sources: string[];
  summary: string;
  status: string;
  dday: number | null;
  is_new: boolean;
  needs_review: boolean;
};

export type ContestResponse = {
  tab: string;
  count: number;
  items: Contest[];
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function fetchContests(tab: string, q = "", tag = ""): Promise<ContestResponse> {
  const params = new URLSearchParams({ tab });
  if (q) params.set("q", q);
  if (tag) params.set("tag", tag);
  const res = await fetch(`${API}/v1/contests?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("목록을 불러오지 못했습니다.");
  }
  return res.json();
}
