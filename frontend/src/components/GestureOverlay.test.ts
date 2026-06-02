import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'

import GestureOverlay from './GestureOverlay.vue'

describe('GestureOverlay', () => {
  it('emits the video element when gesture mode is enabled after mount', async () => {
    const wrapper = mount(GestureOverlay, {
      props: {
        enabled: false,
        cameraReady: false,
        currentGesture: '',
        error: '',
      },
    })

    expect(wrapper.find('video').exists()).toBe(false)

    await wrapper.setProps({ enabled: true })
    await nextTick()

    const emitted = wrapper.emitted('videoReady')
    expect(wrapper.find('video').exists()).toBe(true)
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]?.[0]).toBeInstanceOf(HTMLVideoElement)
  })
})
