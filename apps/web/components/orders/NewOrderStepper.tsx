'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { OrderFormData, INITIAL_ORDER_FORM_DATA, CreateOrderResponse } from '@/lib/types'
import { apiFetch, ApiError } from '@/lib/api'
import { SkillStep } from './steps/SkillStep'
import { RobotStep } from './steps/RobotStep'
import { CoverageStep } from './steps/CoverageStep'
import { VolumeQualityStep } from './steps/VolumeQualityStep'
import { RightsStep } from './steps/RightsStep'
import { ReviewStep } from './steps/ReviewStep'
import { AcquisitionStep } from './steps/AcquisitionStep'
import { OutputStep } from './steps/OutputStep'

const STEP_TITLES = [
  'What should the robot do?',
  'Which robot and hand?',
  'Which objects and viewpoints?',
  'How should Terac collect it?',
  'How many episodes and what quality bar?',
  'What should FORGE deliver?',
  'Who owns the data?',
  'Does this look right?',
]

interface NewOrderStepperProps {
  token: string
}

export function NewOrderStepper({ token }: NewOrderStepperProps) {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<OrderFormData>(INITIAL_ORDER_FORM_DATA)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const router = useRouter()

  function update<K extends keyof OrderFormData>(key: K, value: OrderFormData[K]) {
    setData((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit() {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await apiFetch<CreateOrderResponse>('/orders', token, {
        method: 'POST',
        body: JSON.stringify({
          skill:                     data.skill,
          embodiment:                data.embodiment,
          volume_validated_episodes: data.volume_validated_episodes,
          acquisition:               data.acquisition,
          output:                    data.output,
          coverage:                  data.coverage,
          quality:                   data.quality,
          rights_profile:            data.rights_profile,
        }),
      })
      if (res.stripe_payment_link) {
        window.location.href = res.stripe_payment_link
      } else {
        router.push(`/orders/${res.order_id}`)
      }
    } catch (err) {
      setSubmitError(
        err instanceof ApiError && err.status < 500
          ? 'Please check your order details and try again.'
          : 'We could not place your order. Please try again in a moment.',
      )
      setSubmitting(false)
    }
  }

  const progress = ((step + 1) / 8) * 100

  return (
    <div className="max-w-xl">
      <div className="mb-2 flex items-center">
        <span className="text-sm text-forge-ink-muted">Step {step + 1} of 8</span>
      </div>
      <div className="w-full bg-forge-surface-soft rounded-pill h-1.5 mb-8" role="progressbar"
           aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={8}>
        <div className="bg-forge-primary rounded-pill h-1.5 transition-all duration-300"
             style={{ width: `${progress}%` }} />
      </div>

      <h2 className="text-xl font-semibold text-forge-ink mb-6">{STEP_TITLES[step]}</h2>

      {step === 0 && (
        <SkillStep data={data.skill} onChange={(v) => update('skill', v)}
                   onNext={() => setStep(1)} />
      )}
      {step === 1 && (
        <RobotStep data={data.embodiment} onChange={(v) => update('embodiment', v)}
                   onNext={() => setStep(2)} onBack={() => setStep(0)} />
      )}
      {step === 2 && (
        <CoverageStep data={data.coverage} onChange={(v) => update('coverage', v)}
                      onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      {step === 3 && (
        <AcquisitionStep data={data.acquisition} onChange={(v) => update('acquisition', v)}
                         onNext={() => setStep(4)} onBack={() => setStep(2)} />
      )}
      {step === 4 && (
        <VolumeQualityStep
          volume={data.volume_validated_episodes}
          quality={data.quality}
          onChangeVolume={(v) => update('volume_validated_episodes', v)}
          onChangeQuality={(v) => update('quality', v)}
          onNext={() => setStep(5)} onBack={() => setStep(3)} />
      )}
      {step === 5 && (
        <OutputStep data={data.output} onChange={(v) => update('output', v)}
                    onNext={() => setStep(6)} onBack={() => setStep(4)} />
      )}
      {step === 6 && (
        <RightsStep data={data.rights_profile} onChange={(v) => update('rights_profile', v)}
                    onNext={() => setStep(7)} onBack={() => setStep(5)} />
      )}
      {step === 7 && (
        <ReviewStep data={data} onBack={() => setStep(6)}
                    onSubmit={handleSubmit} submitting={submitting} error={submitError} />
      )}
    </div>
  )
}
