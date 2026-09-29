import { redirect } from "next/navigation";
import { USUARIO_DEMO } from "@/lib/demo";

export default function Demo() {
  redirect(`/conta/${USUARIO_DEMO}`);
}
