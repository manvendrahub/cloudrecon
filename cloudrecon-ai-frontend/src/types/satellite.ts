export type ProcessingStatus = 'Completed' | 'Processing' | 'Queued' | 'Failed'

export interface SatelliteJob {
  id: string
  filename: string
  status: ProcessingStatus
  cloudCoverage: number
  reconstructionScore: number
  date: string
  duration?: string
}