/**
 * Legacy route — redirects to the new complaints flow.
 * Kept so any old bookmarks or links don't 404.
 */
import { redirect } from 'next/navigation'

export default function LegacyComplaintPage() {
  redirect('/complaints/new')
}
