"use client";

import { FormEvent, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function SubmitPage() {
  const [status, setStatus] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {
      title: String(form.get("title") || ""),
      organizer: String(form.get("organizer") || ""),
      url: String(form.get("url") || ""),
      note: String(form.get("note") || ""),
    };
    const res = await fetch(`${API}/v1/submissions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setStatus(res.ok ? "제보가 저장되었습니다." : "저장에 실패했습니다.");
  }

  return (
    <main className="wrap">
      <h1>공모전 제보</h1>
      <p className="meta">크롤러가 놓친 교내·비공개 채널 대회를 부원이 직접 올릴 수 있습니다.</p>
      <form onSubmit={onSubmit} className="card" style={{ maxWidth: 520 }}>
        <input className="search" name="title" placeholder="공모전명" required />
        <input className="search" name="organizer" placeholder="주최" />
        <input className="search" name="url" type="url" placeholder="https://" required />
        <input className="search" name="note" placeholder="메모 (선택)" />
        <button className="btn" type="submit">
          보내기
        </button>
        {status ? <p className="meta">{status}</p> : null}
      </form>
    </main>
  );
}
