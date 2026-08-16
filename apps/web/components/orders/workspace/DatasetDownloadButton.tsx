'use client'

import { useState } from 'react'
import { Download } from 'lucide-react'
import { apiFetch, ApiError } from '@/lib/api'
import { DeliveryResponse } from '@/lib/types'
import { Button } from '@/components/ui/Button'

export function DatasetDownloadButton({ deliveryId, label = 'Download dataset' }: { deliveryId: string | null; label?: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function download() {
    if (!deliveryId) return
    setLoading(true)
    setError(null)
    try {
      const tokenResponse = await fetch('/api/token', { cache: 'no-store' })
      if (!tokenResponse.ok) throw new ApiError(tokenResponse.status, 'Authentication expired')
      const { token } = await tokenResponse.json() as { token: string }
      const delivery = await apiFetch<DeliveryResponse>(`/deliveries/${deliveryId}`, token)
      window.location.assign(delivery.download_url)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not create a secure download link')
      setLoading(false)
    }
  }

  return (
    <div>
      <Button variant="secondary" onClick={download} disabled={!deliveryId} loading={loading} className="text-sm">
        {!loading && <Download size={16} aria-hidden="true" />}
        {label}
      </Button>
      {error && <p className="mt-2 max-w-xs text-sm text-forge-danger" role="alert">{error}</p>}
    </div>
  )
}
