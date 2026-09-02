import { ContestBoard } from "../../components/ContestBoard";

export default async function ContestsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; q?: string; tag?: string }>;
}) {
  const params = await searchParams;
  return (
    <ContestBoard
      tab={params.tab || "all"}
      q={params.q || ""}
      tag={params.tag || ""}
    />
  );
}
