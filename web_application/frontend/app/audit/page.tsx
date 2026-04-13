/**
 * Legacy audit route — audit trail is now embedded in the complaint detail page.
 * Redirects to the complaints list so old links don't 404.
 */
import { redirect } from 'next/navigation'

export default function LegacyAuditPage() {
  redirect('/complaints')
}
